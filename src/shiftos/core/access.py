"""Explicit operator scopes, not named-user identity or database row security.

Legacy behaviour is retained only for local development/tests. Deployment uses
an operator-managed policy containing token hashes and explicit institution and
operation grants. Reference/source administration is deliberately global-admin
only because the existing reference store has no tenant ownership field.
"""

import hashlib
import hmac
import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from shiftos.core.errors import DomainError
from shiftos.db.session import get_session
from shiftos.models import (
    ActionPlanRun,
    AnalysisRun,
    CareerRecommendation,
    CareerRun,
    Course,
    Institution,
    Job,
    Programme,
    ProgrammeRevision,
)

Permission = Literal["read", "write", "review", "admin"]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")]
BEARER = HTTPBearer(
    auto_error=False,
    description=(
        "Opaque operator credential required in scoped API mode; "
        "this does not establish named academic identity."
    ),
)


class AccessPrincipal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    principal_id: Identifier
    token_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] = Field(repr=False)
    institution_ids: frozenset[UUID] = Field(default_factory=frozenset, max_length=100)
    permissions: frozenset[Permission] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def explicit_scope(self):
        if "admin" not in self.permissions and not self.institution_ids:
            raise ValueError("An institution scope or explicit global admin grant is required")
        if not self.permissions & {"read", "write", "review"}:
            raise ValueError("Admin requires separate explicit operation permissions")
        return self


class AccessPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    version: Literal["phase7-access-1"]
    principals: list[AccessPrincipal] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_grants(self):
        if len({row.principal_id for row in self.principals}) != len(self.principals) or len(
            {row.token_sha256 for row in self.principals}
        ) != len(self.principals):
            raise ValueError("Principal identifiers and token hashes must be unique")
        return self


def _policy(settings):
    try:
        path = settings.api_access_policy_path
        if path is None or path.stat().st_size > 100_000:
            raise ValueError
        return AccessPolicy.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (AttributeError, OSError, TypeError, ValueError):
        raise DomainError(
            "ACCESS_POLICY_INVALID",
            "Configure a valid explicit API access policy before using scoped access",
            503,
        ) from None


def validate_access_configuration(settings) -> dict:
    """Return safe readiness counts; never credentials, token hashes or institution IDs."""
    mode = getattr(settings, "api_access_mode", "legacy")
    if mode == "legacy":
        if settings.app_env == "production":
            raise DomainError(
                "ACCESS_POLICY_REQUIRED",
                "Production requires explicit scoped API access; legacy access is local only",
                503,
            )
        return {"mode": "legacy", "ready": False, "production_eligible": False}
    if mode != "scoped":
        raise DomainError("ACCESS_POLICY_INVALID", "Configure a supported API access mode", 503)
    policy = _policy(settings)
    return {
        "mode": "scoped",
        "ready": True,
        "production_eligible": True,
        "principal_count": len(policy.principals),
        "global_admin_count": sum("admin" in row.permissions for row in policy.principals),
    }


def authenticate(request: Request) -> AccessPrincipal | None:
    """Resolve one request grant without treating the alias as a named academic."""
    settings = request.app.state.settings
    if getattr(settings, "api_access_mode", "legacy") == "legacy":
        if settings.app_env == "production":
            validate_access_configuration(settings)
        return None
    cached = getattr(request.state, "access_principal", None)
    if cached is not None:
        return cached
    policy = _policy(settings)
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if (
        scheme.lower() != "bearer"
        or not 32 <= len(token) <= 4096
        or any(character.isspace() or ord(character) < 33 for character in token)
    ):
        raise DomainError("NOT_AUTHORIZED", "A scoped bearer credential is required", 401)
    supplied = hashlib.sha256(token.encode("utf-8")).hexdigest()
    found = None
    for principal in policy.principals:
        if hmac.compare_digest(principal.token_sha256, supplied):
            found = principal
    if found is None:
        raise DomainError("NOT_AUTHORIZED", "A scoped bearer credential is required", 401)
    request.state.access_principal = found
    return found


def require_permission(principal, permission):
    if permission not in principal.permissions:
        raise DomainError(
            "FORBIDDEN", "This operator grant does not allow the requested operation", 403
        )


def scope_statement(request, statement, institution_column):
    """Filter global listings before count/pagination, never hide rows afterwards."""
    principal = authenticate(request)
    if principal is None or "admin" in principal.permissions:
        return statement
    return statement.where(institution_column.in_(principal.institution_ids))


def _uuid(value):
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise DomainError("VALIDATION_ERROR", "Supply a valid resource identifier", 422) from None


async def require_api_access(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    _bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER)] = None,
):
    """Apply method and object-owner checks before a scoped route reads/writes data."""
    principal = authenticate(request)
    if principal is None:
        return
    parts = request.url.path.strip("/").split("/")[2:]
    operation = (
        "read"
        if request.method in {"GET", "HEAD", "OPTIONS"}
        or request.method == "POST"
        and len(parts) == 3
        and parts[0] == "programmes"
        and parts[-1] == "replay-assessment"
        else "review"
        if parts and parts[-1] == "reviews"
        else "write"
    )
    require_permission(principal, operation)
    if "admin" in principal.permissions:
        return
    if not parts:
        raise DomainError("FORBIDDEN", "This API resource requires an explicit admin grant", 403)
    family = parts[0]
    if (
        family in {"sources", "evidence"}
        or (family == "institutions" and len(parts) == 1 and operation != "read")
        or (family == "catalogue" and parts[1:] != ["providers"] and parts[1:2] != ["jobs"])
    ):
        raise DomainError(
            "FORBIDDEN", "This operation requires an explicit global admin grant", 403
        )
    institution_id = None
    if family == "institutions" and len(parts) > 1:
        institution_id = _uuid(parts[1])
    elif family == "programmes" and len(parts) == 1:
        if operation != "read":
            try:
                payload = await request.json()
                institution_id = _uuid(payload["institution_id"])
            except (KeyError, TypeError, ValueError):
                raise DomainError(
                    "VALIDATION_ERROR", "Supply a valid programme institution", 422
                ) from None
    elif family == "programmes":
        institution_id = session.scalar(
            select(Programme.institution_id).where(Programme.id == _uuid(parts[1]))
        )
    elif family == "courses" and len(parts) > 1:
        institution_id = session.scalar(
            select(Programme.institution_id)
            .join(ProgrammeRevision, ProgrammeRevision.programme_id == Programme.id)
            .join(Course, Course.programme_revision_id == ProgrammeRevision.id)
            .where(Course.id == _uuid(parts[1]))
        )
    elif family in {"analyses", "career-analyses", "action-plans"} and len(parts) > 1:
        model = {
            "analyses": AnalysisRun,
            "career-analyses": CareerRun,
            "action-plans": ActionPlanRun,
        }[family]
        institution_id = session.scalar(
            select(model.institution_id).where(model.id == _uuid(parts[1]))
        )
    elif family == "career-recommendations" and len(parts) > 1:
        institution_id = session.scalar(
            select(CareerRun.institution_id)
            .join(CareerRecommendation, CareerRecommendation.run_id == CareerRun.id)
            .where(CareerRecommendation.id == _uuid(parts[1]))
        )
    elif family == "catalogue" and parts[1:2] == ["jobs"] and len(parts) > 2:
        institution_id = session.scalar(select(Job.institution_id).where(Job.id == _uuid(parts[2])))
    elif family == "catalogue" and parts[1:] == ["providers"]:
        return
    elif family not in {"institutions", "programmes"}:
        raise DomainError("FORBIDDEN", "This API resource requires an explicit admin grant", 403)
    # Only the two explicitly filtered global lists have no object owner.
    if len(parts) == 1 and family in {"institutions", "programmes"} and operation == "read":
        return
    if institution_id not in principal.institution_ids:
        raise DomainError("NOT_FOUND", "The requested resource was not found", 404)
    academic_create = request.method == "POST" and (
        parts == ["programmes"]
        or len(parts) == 3
        and family in {"institutions", "programmes"}
        and parts[-1] in {"programmes", "courses"}
    )
    if academic_create:
        payload = await request.json()
        if isinstance(payload, dict) and payload.get("source_id") is not None:
            source_id = _uuid(payload["source_id"])
            owned = (
                select(Institution.source_id)
                .where(Institution.id == institution_id, Institution.source_id == source_id)
                .union_all(
                    select(Programme.source_id).where(
                        Programme.institution_id == institution_id, Programme.source_id == source_id
                    ),
                    select(Course.source_id)
                    .join(ProgrammeRevision, ProgrammeRevision.id == Course.programme_revision_id)
                    .join(Programme, Programme.id == ProgrammeRevision.programme_id)
                    .where(
                        Programme.institution_id == institution_id, Course.source_id == source_id
                    ),
                )
                .exists()
            )
            if not session.scalar(select(owned)):
                raise DomainError("NOT_FOUND", "The requested source was not found", 404)
