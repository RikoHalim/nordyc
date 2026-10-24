"""Bounded judge-owned upload tenants, never credentials or academic approval.

Session metadata and quota reservations use terminal administrative Job rows;
the normal worker never claims these kinds. No database schema is added.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import func, select, text

from shiftos.core.access import AccessPrincipal
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import CareerRun, Institution, Job, Programme
from shiftos.services.ingestion.catalogue import check_origin

COOKIE = "nordyc_upload_session"
SESSION_KIND = "PUBLIC_UPLOAD_SESSION"
RESERVATION_KIND = "PUBLIC_UPLOAD_RESERVATION"
SESSION_SECONDS = 3600
UPLOAD_LIMIT = 3
SUBMISSION_LIMIT = 12
MAX_SESSIONS = 100
MAX_GLOBAL_UPLOADS = 30
MAX_GLOBAL_SUBMISSIONS = 500
PUBLIC_JOB_KINDS = {"CURRICULUM_PDF_UPLOAD", "PROGRAMME_ANALYSIS", "CAREER_ANALYSIS", "ACTION_PLAN"}
_LOCK = threading.RLock()


class PublicUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    institution_name: str = Field(min_length=2, max_length=255)
    institution_url: HttpUrl
    programme_name: str = Field(min_length=2, max_length=255)
    programme_url: HttpUrl
    permitted_public_document: bool

    @field_validator("institution_name", "programme_name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("A user-attributed name is required")
        return value

    @field_validator("institution_url", "programme_url")
    @classmethod
    def public_origin(cls, value):
        host = (value.host or "").lower().rstrip(".")
        if (
            value.scheme != "https"
            or value.username
            or value.password
            or value.fragment
            or not host
            or "." not in host
            or host.endswith((".localhost", ".local", ".internal"))
        ):
            raise ValueError("Supply an HTTPS public origin without embedded credentials")
        try:
            ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            return value
        raise ValueError("Official origin metadata requires a public domain name")


def session_secret() -> bytes:
    value = os.environ.get("NORDYC_UPLOAD_SESSION_SECRET") or os.environ.get("SESSION_SECRET", "")
    if len(value) < 32:
        raise ValueError(
            "Judge uploads require a persistent server session secret of at least 32 characters"
        )
    return hmac.digest(value.encode(), b"NORDYC:public-upload-session:v1", "sha256")


def same_origin(request) -> bool:
    from urllib.parse import urlsplit

    try:
        origin = urlsplit(request.headers.get("origin", ""))
        host = request.headers.get("host", "").lower()
        return (
            request.headers.get("sec-fetch-site", "same-origin") not in {"cross-site", "same-site"}
            and origin.netloc.lower() == host
            and not origin.username
            and not origin.password
            and not origin.path
            and not origin.query
            and not origin.fragment
            and (
                origin.scheme == "https"
                or origin.scheme == "http"
                and origin.hostname in {"127.0.0.1", "localhost", "testserver"}
            )
        )
    except ValueError:
        return False


def _failure(code="FORBIDDEN", status=403):
    return DomainError(
        code, "This judge upload session cannot perform the requested action", status
    )


@contextmanager
def _transaction(database):
    with _LOCK, database.session_factory() as session, session.begin():
        if session.bind.dialect.name == "postgresql":
            session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 784225901})
        yield session


def _pack(payload, secret):
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(
        b"="
    )
    signature = base64.urlsafe_b64encode(hmac.digest(secret, body, "sha256")).rstrip(b"=")
    return (body + b"." + signature).decode()


def _unpack(cookie, secret):
    try:
        if not cookie or len(cookie) > 2048:
            return None
        body, signature = cookie.encode("ascii").split(b".")
        expected = base64.urlsafe_b64encode(hmac.digest(secret, body, "sha256")).rstrip(b"=")
        if not hmac.compare_digest(expected, signature):
            return None
        value = json.loads(base64.urlsafe_b64decode(body + b"=" * (-len(body) % 4)))
        if set(value) != {"id", "nonce", "exp"} or not isinstance(value["exp"], int):
            return None
        if value["exp"] <= int(datetime.now(UTC).timestamp()):
            return None
        UUID(value["id"])
        if not isinstance(value["nonce"], str) or not 32 <= len(value["nonce"]) <= 100:
            return None
        return value
    except (ValueError, TypeError, UnicodeError, KeyError):
        return None


def resolve_session(database, cookie, secret):
    value = _unpack(cookie, secret)
    if value is None:
        return None
    with database.session_factory() as session:
        marker = session.get(Job, UUID(value["id"]))
        if marker is None or marker.kind != SESSION_KIND or marker.status != JobStatus.SUCCEEDED:
            return None
        payload = marker.payload_json
        if payload.get("expires_at") != value["exp"] or not hmac.compare_digest(
            str(payload.get("nonce_sha256", "")),
            hashlib.sha256(value["nonce"].encode()).hexdigest(),
        ):
            return None
        programme = session.get(Programme, UUID(payload["programme_id"]))
        if not programme or programme.institution_id != marker.institution_id:
            return None
        return {
            "id": marker.id,
            "institution_id": marker.institution_id,
            "programme_id": programme.id,
            "expires_at": value["exp"],
        }


def principal_for(upload_session, example_institution, *, mutation=False):
    scopes = {upload_session["institution_id"]}
    if not mutation:
        scopes.add(example_institution)
    return AccessPrincipal(
        principal_id="public-upload-" + str(upload_session["id"]),
        token_sha256="0" * 64,
        institution_ids=frozenset(scopes),
        permissions=frozenset({"read", "write"}),
    )


def create_session(database, value: PublicUploadRequest, secret, client_ip):
    if not value.permitted_public_document:
        raise _failure("VALIDATION_ERROR", 422)
    if value.institution_url.scheme != "https" or value.programme_url.scheme != "https":
        raise _failure("VALIDATION_ERROR", 422)
    now = datetime.now(UTC)
    expires = int((now + timedelta(seconds=SESSION_SECONDS)).timestamp())
    ip_hash = hmac.new(secret, ("rate:" + client_ip).encode(), "sha256").hexdigest()
    nonce = secrets.token_urlsafe(32)
    with _transaction(database) as session:
        count = session.scalar(
            select(func.count()).select_from(Job).where(Job.kind == SESSION_KIND)
        )
        if count >= MAX_SESSIONS:
            raise _failure("JUDGE_CAPACITY_REACHED", 429)
        recent = session.scalars(
            select(Job)
            .where(Job.kind == SESSION_KIND, Job.created_at >= now - timedelta(hours=1))
            .limit(MAX_SESSIONS)
        ).all()
        if sum(row.payload_json.get("ip_hash") == ip_hash for row in recent) >= 5:
            raise _failure("JUDGE_RATE_LIMITED", 429)
        institution = Institution(
            name=value.institution_name.strip(),
            website_url=str(value.institution_url),
            is_synthetic=False,
            source_locator="Judge-provided identity and origin; not independently verified",
        )
        check_origin(institution, str(value.programme_url))
        session.add(institution)
        session.flush()
        programme = Programme(
            institution_id=institution.id,
            name=value.programme_name.strip(),
            canonical_url=str(value.programme_url),
            is_synthetic=False,
            source_locator="Judge-provided programme identity; PDF contents remain unreviewed",
        )
        session.add(programme)
        session.flush()
        marker = Job(
            institution_id=institution.id,
            kind=SESSION_KIND,
            status=JobStatus.SUCCEEDED,
            started_at=now,
            completed_at=now,
            is_synthetic=False,
            payload_json={
                "programme_id": str(programme.id),
                "expires_at": expires,
                "nonce_sha256": hashlib.sha256(nonce.encode()).hexdigest(),
                "ip_hash": ip_hash,
                "permitted_public_document": True,
            },
            result_json={},
        )
        session.add(marker)
        session.flush()
        result = {
            "programme_id": str(programme.id),
            "institution_id": str(institution.id),
            "expires_in_seconds": SESSION_SECONDS,
        }
        cookie = _pack({"id": str(marker.id), "nonce": nonce, "exp": expires}, secret)
    return result, cookie


def reserve_submission(database, upload_session, path, payload=None):
    programme = str(upload_session["programme_id"])
    allowed = {
        f"/api/v1/programmes/{programme}/curriculum-pdf": "upload",
        f"/api/v1/programmes/{programme}/analyses": "analysis",
        f"/api/v1/programmes/{programme}/career-analyses": "career",
    }
    kind = allowed.get(path)
    with _transaction(database) as session:
        if (
            kind is None
            and path.startswith("/api/v1/career-analyses/")
            and path.endswith("/action-plans")
        ):
            try:
                career = session.get(CareerRun, UUID(path.split("/")[4]))
            except ValueError:
                raise _failure() from None
            if (
                career
                and career.programme_id == upload_session["programme_id"]
                and career.institution_id == upload_session["institution_id"]
            ):
                kind = "plan"
        if kind is None:
            raise _failure()
        if kind != "upload":
            if not isinstance(payload, dict) or payload.get("mode") != "offline":
                raise _failure()
            fields = {
                "analysis": {"revision_id", "mode", "research", "idempotency_key"},
                "career": {"revision_id", "mode", "idempotency_key"},
                "plan": {"mode", "phase4_analysis_id", "idempotency_key"},
            }[kind]
            if set(payload) - fields or kind == "analysis" and payload.get("research") is not False:
                raise _failure()
        reservations = session.scalars(
            select(Job).where(Job.kind == RESERVATION_KIND).limit(MAX_GLOBAL_SUBMISSIONS + 1)
        ).all()
        own = [
            row for row in reservations if row.institution_id == upload_session["institution_id"]
        ]
        uploads = sum(row.payload_json.get("kind") == "upload" for row in reservations)
        if (
            len(reservations) >= MAX_GLOBAL_SUBMISSIONS
            or len(own) >= SUBMISSION_LIMIT
            or kind == "upload"
            and (
                uploads >= MAX_GLOBAL_UPLOADS
                or sum(row.payload_json.get("kind") == "upload" for row in own) >= UPLOAD_LIMIT
            )
        ):
            raise _failure("JUDGE_CAPACITY_REACHED", 429)
        now = datetime.now(UTC)
        if upload_session["expires_at"] <= int(now.timestamp()):
            raise _failure("NOT_AUTHORIZED", 401)
        session.add(
            Job(
                institution_id=upload_session["institution_id"],
                kind=RESERVATION_KIND,
                status=JobStatus.SUCCEEDED,
                started_at=now,
                completed_at=now,
                is_synthetic=False,
                payload_json={"kind": kind, "session_id": str(upload_session["id"])},
                result_json={},
            )
        )


def active_session_institutions(database):
    now = int(datetime.now(UTC).timestamp())
    with database.session_factory() as session:
        rows = session.scalars(
            select(Job)
            .where(Job.kind == SESSION_KIND, Job.status == JobStatus.SUCCEEDED)
            .limit(MAX_SESSIONS)
        ).all()
        return {row.institution_id for row in rows if row.payload_json.get("expires_at", 0) > now}
