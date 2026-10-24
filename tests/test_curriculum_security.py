"""Offline boundary/security checks for Phase 2 writes and request buffering."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select

from shiftos.api.body_limit import BodyLimitMiddleware
from shiftos.core.config import Settings
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.main import create_app
from shiftos.models import Course, Document, DocumentAnchor, Institution, Job, Programme, Source
from shiftos.repositories.catalogue import canonical_url
from shiftos.schemas.ingestion import CatalogueResult
from shiftos.services.ingestion import worker
from shiftos.services.ingestion.catalogue import check_origin
from shiftos.services.ingestion.fetcher import FetchedPage

TOKEN = "synthetic-local-security-test-token-no-live-credential"


def manifest(**updates):
    value = {
        "name": "Synthetic degree for security tests",
        "canonical_url": "https://catalogue.invalid/degree",
        "source_url": "https://catalogue.invalid/degree",
        "source_locator": "Main Courses",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "reviewed": True,
        "courses": [
            {
                "course_name": "Synthetic Ethics",
                "source_locator": "Main Courses / Year 1 / row 1",
                "source_excerpt": "Synthetic Ethics",
            }
        ],
    }
    return {**value, **updates}


def production_client(database, tmp_path, token=None):
    # Settings keeps its valid PostgreSQL default URL; the injected isolated
    # SQLite database supplies the offline test storage.
    policy_path = tmp_path / "synthetic-access-policy.json"
    if token:
        policy_path.write_text(
            json.dumps(
                {
                    "version": "phase7-access-1",
                    "principals": [
                        {
                            "principal_id": "synthetic-test-operator",
                            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
                            "permissions": ["read", "write", "review", "admin"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    settings = Settings(
        _env_file=None,
        app_env="production",
        catalogue_write_token=token,
        api_access_mode="scoped" if token else "legacy",
        api_access_policy_path=policy_path if token else None,
    )
    return TestClient(create_app(settings=settings, database=database))


def invoke_body_limit(chunks, *, limit=8, method="POST"):
    """Exercise ASGI receive frames directly, including genuine chunked input."""
    calls = []
    sent = []
    messages = list(chunks)

    async def receive():
        return messages.pop(0) if messages else {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    async def app(scope, upstream_receive, upstream_send):
        calls.append(await upstream_receive())
        await upstream_send({"type": "http.response.start", "status": 204, "headers": []})
        await upstream_send({"type": "http.response.body", "body": b""})

    scope = {"type": "http", "method": method, "headers": [], "path": "/synthetic"}
    asyncio.run(BodyLimitMiddleware(app, max_bytes=limit)(scope, receive, send))
    return calls, sent


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
def test_body_limit_rejects_oversize_chunked_input_before_downstream(method):
    calls, sent = invoke_body_limit(
        [
            {"type": "http.request", "body": b"12345", "more_body": True},
            {"type": "http.request", "body": b"6789", "more_body": False},
        ],
        method=method,
    )
    assert calls == []
    assert sent[0]["status"] == 413
    headers = dict(sent[0]["headers"])
    assert UUID(headers[b"x-request-id"].decode())
    payload = json.loads(sent[1]["body"])
    assert payload["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert payload["error"]["details"] == []


def test_body_limit_replays_exact_boundary_chunked_body_once():
    calls, sent = invoke_body_limit(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"", "more_body": True},
            {"type": "http.request", "body": b"45678", "more_body": False},
        ]
    )
    assert calls == [{"type": "http.request", "body": b"12345678", "more_body": False}]
    assert sent[0]["status"] == 204


def test_disconnected_upload_is_not_processed():
    calls, sent = invoke_body_limit(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.disconnect"},
        ]
    )
    assert calls == []
    assert sent == []


def test_fastapi_size_limit_precedes_json_decoding(client):
    response = client.post(
        "/api/v1/catalogue/discover",
        content=b"not-json" + b"x" * 1_048_576,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert UUID(response.headers["X-Request-ID"])


@pytest.mark.parametrize("token", [None, "wrong-synthetic-token"])
@pytest.mark.parametrize(
    "endpoint",
    [
        "/catalogue/discover",
        "/institutions/{id}/discover",
        "/institutions/{id}/imports",
        "/programmes/{id}/imports",
    ],
)
def test_production_write_requires_matching_token_without_creating_records(
    database, tmp_path, token, endpoint
):
    if endpoint.endswith("/imports"):
        body = manifest() if endpoint.startswith("/programmes/") else {"programmes": [manifest()]}
    else:
        body = {"provider": "xmum"}
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    with production_client(database, tmp_path, TOKEN) as client:
        response = client.post(
            "/api/v1" + endpoint.replace("{id}", str(uuid4())), json=body, headers=headers
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHORIZED"
    assert TOKEN not in response.text
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Job)) == 0
        assert session.scalar(select(func.count()).select_from(Institution)) == 0


def test_unconfigured_production_writes_fail_closed(database, tmp_path):
    with pytest.raises(DomainError) as error:
        production_client(database, tmp_path)
    assert error.value.status_code == 503
    assert error.value.code == "ACCESS_POLICY_REQUIRED"


def test_matching_production_token_can_enqueue_but_does_not_fetch(database, tmp_path):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with production_client(database, tmp_path, TOKEN) as client:
        response = client.post(
            "/api/v1/catalogue/discover",
            json={"provider": "xmum"},
            headers=headers,
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "QUEUED"
        assert client.get(f"/api/v1/catalogue/jobs/{payload['id']}").status_code == 401
        read = client.get(f"/api/v1/catalogue/jobs/{payload['id']}", headers=headers)
    assert read.status_code == 200
    assert "payload_json" not in read.json()
    assert TOKEN not in response.text + read.text


@pytest.mark.parametrize("field", ["source_url", "canonical_url"])
def test_origin_errors_do_not_expose_url_credentials_or_import_payload(client, field):
    institution = client.post(
        "/api/v1/institutions",
        json={
            "name": "Synthetic Security University",
            "website_url": "https://catalogue.invalid",
            "is_synthetic": True,
        },
    ).json()
    secret = "sentinel-source-password"
    response = client.post(
        f"/api/v1/institutions/{institution['id']}/imports",
        json={
            "is_synthetic": True,
            "programmes": [manifest(**{field: f"https://user:{secret}@catalogue.invalid/degree"})],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert secret not in response.text
    assert "user:" not in response.text


def test_validation_error_omits_rejected_source_url_and_private_details(client):
    secret = "sentinel-invalid-url-password"
    response = client.post(
        f"/api/v1/institutions/{uuid4()}/imports",
        json={"programmes": [manifest(source_url=f"private invalid user:{secret}")]},
    )
    assert response.status_code == 422
    assert secret not in response.text
    assert all(
        set(item) == {"location", "type", "message"} for item in response.json()["error"]["details"]
    )


@pytest.mark.parametrize("token", ["", " ", "\t\n"])
def test_blank_authorization_tokens_cannot_enable_production_writes(token):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", catalogue_write_token=token)


def test_origin_check_rejects_empty_raw_url_userinfo():
    # Pydantic removes empty userinfo during URL normalization. Exercise the
    # lower-level guard directly because discovered/raw strings also use it.
    institution = Institution(
        name="Synthetic Userinfo University",
        website_url="https://catalogue.invalid",
        is_synthetic=True,
    )
    with pytest.raises(DomainError) as error:
        check_origin(institution, "https://:@catalogue.invalid/degree")
    assert error.value.code == "VALIDATION_ERROR"


def test_canonical_identity_keeps_meaningful_programme_query_parameters():
    # Future providers may use one programme path with a distinct programme ID.
    first = canonical_url("https://www.catalogue.invalid/programme?id=1")
    second = canonical_url("https://catalogue.invalid/programme?id=2")
    assert first != second
    assert "id=1" in first
    assert "id=2" in second


def failed_job(database, *, kind="CURRICULUM_IMPORT", status=JobStatus.FAILED):
    now = datetime.now(UTC)
    with database.session_factory() as session:
        institution = Institution(
            name="Synthetic Stale Worker University",
            website_url="https://catalogue.invalid",
            is_synthetic=True,
        )
        session.add(institution)
        session.flush()
        job = Job(
            institution_id=institution.id,
            kind=kind,
            status=status,
            is_synthetic=True,
            started_at=now - timedelta(hours=2),
            completed_at=now if status == JobStatus.FAILED else None,
            error="STALE_WORKER" if status == JobStatus.FAILED else None,
            payload_json={"is_synthetic": True, "programmes": [manifest()]}
            if kind == "CURRICULUM_IMPORT"
            else {"provider": "xmum"},
        )
        session.add(job)
        session.commit()
        session.expunge(job)
        return job


def assert_no_curriculum_writes(database):
    with database.session_factory() as session:
        for model in (Programme, Course, Source, Document, DocumentAnchor):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_failed_manual_worker_cannot_commit_a_programme_before_progress_check(database):
    job = failed_job(database)
    with pytest.raises(DomainError) as error:
        worker._manual(database, job)
    assert error.value.code == "CONFLICT"
    assert_no_curriculum_writes(database)
    with database.session_factory() as session:
        stored = session.get(Job, job.id)
        assert stored.status == JobStatus.FAILED
        assert stored.error == "STALE_WORKER"


def test_discovery_fenced_after_job_fails_during_directory_fetch(database, monkeypatch):
    job = failed_job(database, kind="CURRICULUM_DISCOVERY", status=JobStatus.RUNNING)
    provider = {
        **worker.PROVIDERS["xmum"],
        "name": "Synthetic Stale Worker University",
        "website_url": "https://catalogue.invalid/",
        "directory_url": "https://catalogue.invalid/undergraduate-programmes",
        "allowed_hosts": ("catalogue.invalid",),
    }
    monkeypatch.setitem(worker.PROVIDERS, "xmum", provider)

    class FakeFetcher:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def fetch_html(self, url):
            # Simulate an operator fencing an abandoned worker while its
            # network operation was in flight; no actual HTTP is performed.
            with database.session_factory() as session:
                stored = session.get(Job, job.id)
                stored.status = JobStatus.FAILED
                stored.completed_at = datetime.now(UTC)
                stored.error = "STALE_WORKER"
                session.commit()
            return FetchedPage(
                url=url,
                html=(
                    '<main><a href="/courses/bachelor-synthetic">'
                    "Bachelor of Synthetic Studies</a></main>"
                ),
                sha256="a" * 64,
                retrieved_at=datetime.now(UTC),
            )

    with pytest.raises(DomainError) as error:
        worker._discover(database, job, Settings(_env_file=None), FakeFetcher)
    assert error.value.code == "CONFLICT"
    assert_no_curriculum_writes(database)
    with database.session_factory() as session:
        stored = session.get(Job, job.id)
        assert stored.status == JobStatus.FAILED
        assert stored.error == "STALE_WORKER"
        assert session.get(Institution, job.institution_id).source_id is None


@pytest.mark.parametrize("status", [JobStatus.QUEUED, JobStatus.FAILED, JobStatus.SUCCEEDED])
def test_running_job_fence_rejects_nonrunning_status(database, status):
    job = failed_job(database, status=status)
    with database.session_factory() as session, pytest.raises(DomainError) as error:
        worker.lock_running_job(session, job.id)
    assert error.value.code == "CONFLICT"


def test_failed_job_progress_is_not_replaced(database):
    job = failed_job(database)
    with database.session_factory() as session:
        stored = session.get(Job, job.id)
        stored.result_json = {"retained_partial_progress": True}
        session.commit()
    with pytest.raises(DomainError):
        worker._save_progress(database, job.id, CatalogueResult(provider="structured_manual"))
    with database.session_factory() as session:
        assert session.get(Job, job.id).result_json == {"retained_partial_progress": True}


def test_worker_finalization_preserves_operator_failure(database, monkeypatch):
    job = failed_job(database, status=JobStatus.QUEUED)

    def stopped_manual(database, detached_job):
        with database.session_factory() as session:
            stored = session.get(Job, detached_job.id)
            stored.status = JobStatus.FAILED
            stored.completed_at = datetime.now(UTC)
            stored.error = "STALE_WORKER"
            stored.result_json = {"retained_partial_progress": True}
            session.commit()
        # The worker's previous work may finish returning after it was fenced.
        return CatalogueResult(provider="structured_manual")

    monkeypatch.setattr(worker, "_manual", stopped_manual)
    assert worker.run_once(database, Settings(_env_file=None)) == job.id
    with database.session_factory() as session:
        stored = session.get(Job, job.id)
        assert stored.status == JobStatus.FAILED
        assert stored.error == "STALE_WORKER"
        assert stored.result_json == {"retained_partial_progress": True}
