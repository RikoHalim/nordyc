"""Runtime/source privacy contracts without external calls or deployment."""

import asyncio
import hashlib
import json
import os
from uuid import uuid4

import httpx
import pytest
from fastapi.openapi.models import OpenAPI
from fastapi.testclient import TestClient
from test_curriculum_upload import content
from test_curriculum_upload import upload_context as private_upload_fixture

from shiftos.api.body_limit import BodyLimitMiddleware
from shiftos.core.config import Settings
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.main import create_app
from shiftos.models import Document, Institution, Job, Programme
from shiftos.services.ingestion.parsers import CurriculumParseError
from shiftos.services.ingestion.pdf_process import prepare_in_process
from shiftos.services.ingestion.uploads import enqueue_pdf_upload, upload_path
from shiftos.services.ingestion.worker import run_once
from shiftos.services.runtime import database_identity, runtime_report

upload_context = private_upload_fixture


def test_request_body_deadline_is_total_and_never_calls_downstream():
    sent = []

    async def receive():
        await asyncio.sleep(0.03)
        return {"type": "http.request", "body": b"x", "more_body": True}

    async def send(message):
        sent.append(message)

    async def downstream(*args):
        pytest.fail("A timed-out request must not reach a handler")

    asyncio.run(
        BodyLimitMiddleware(downstream, read_timeout_seconds=0.005)(
            {"type": "http", "method": "POST", "path": "/api/v1/institutions", "headers": []},
            receive,
            send,
        )
    )
    assert sent[0]["status"] == 408
    assert json.loads(sent[1]["body"])["error"]["code"] == "REQUEST_TIMEOUT"


def test_same_pdf_is_isolated_between_scoped_institution_storage(session, upload_context):  # noqa: F811
    _, settings, programme_id = upload_context
    scoped = settings.model_copy(update={"api_access_mode": "scoped"})
    other = Institution(
        name="Second Fictional University", website_url="https://example.invalid", is_synthetic=True
    )
    session.add(other)
    session.flush()
    programme = Programme(
        institution_id=other.id,
        name="Second fictional programme",
        canonical_url="https://example.invalid/second",
        is_synthetic=True,
    )
    session.add(programme)
    session.commit()
    first = enqueue_pdf_upload(session, programme_id, content(), scoped)
    second = enqueue_pdf_upload(session, programme.id, content(), scoped)
    checksum = hashlib.sha256(content()).hexdigest()
    first_path = upload_path(scoped, checksum, first.institution_id)
    second_path = upload_path(scoped, checksum, second.institution_id)
    assert first_path != second_path and first_path.read_bytes() == second_path.read_bytes()
    assert (
        first.payload_json["storage_scope"] == second.payload_json["storage_scope"] == "institution"
    )
    if os.name != "nt":
        assert first_path.stat().st_mode & 0o077 == 0
        assert first_path.parent.stat().st_mode & 0o077 == 0


def test_scoped_pdf_worker_uses_bounded_child_process_and_private_namespace(
    database,
    session,
    upload_context,  # noqa: F811
):
    _, settings, programme_id = upload_context
    scoped = settings.model_copy(update={"api_access_mode": "scoped"})
    job = enqueue_pdf_upload(session, programme_id, content(), scoped)
    assert run_once(database, scoped) == job.id
    session.expire_all()
    assert session.get(Job, job.id).status == JobStatus.SUCCEEDED
    documents = session.query(Document).filter(Document.storage_path.is_not(None)).all()
    assert any(str(job.institution_id) in row.storage_path for row in documents)


def test_pdf_child_timeout_never_receives_provider_secrets(monkeypatch):
    import subprocess

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "private-sentinel")
    monkeypatch.setenv("AI_INTEGRATIONS_ANTHROPIC_API_KEY", "private-model-sentinel")

    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == 30
        assert not any(
            key in kwargs["env"]
            for key in ("BRAVE_SEARCH_API_KEY", "AI_INTEGRATIONS_ANTHROPIC_API_KEY", "DATABASE_URL")
        )
        raise subprocess.TimeoutExpired(args[0], 30)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(CurriculumParseError) as error:
        prepare_in_process(content(), regions=None, metadata={})
    assert error.value.code == "pdf_processing_timeout"


def test_pdf_original_error_code_survives_sanitized_child_boundary(monkeypatch):
    import subprocess

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args, returncode=0, stdout=b'{"error":"pdf_page_limit"}'
        ),
    )
    with pytest.raises(CurriculumParseError) as error:
        prepare_in_process(content(), regions=None, metadata={})
    assert error.value.code == "pdf_page_limit"


def test_existing_hardlinked_upload_object_cannot_read_or_adopt_another_file(
    session,
    upload_context,
    tmp_path,  # noqa: F811
):
    _, settings, programme_id = upload_context
    raw = content()
    outside = tmp_path / "unrelated.pdf"
    outside.write_bytes(raw)
    target = upload_path(settings, hashlib.sha256(raw).hexdigest())
    target.parent.mkdir(parents=True)
    os.link(outside, target)
    with pytest.raises(DomainError, match="unsafe"):
        enqueue_pdf_upload(session, programme_id, raw, settings)
    assert outside.read_bytes() == raw


def test_runtime_preflight_is_secret_free_and_never_contacts_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Runtime configuration inspection must not use HTTP")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    settings = Settings(
        _env_file=None,
        analysis_model_provider="replit_claude",
        database_url="postgresql+psycopg://operator:private-sentinel@db.example.invalid/fixture",
        replit_anthropic_api_key="private-provider-sentinel",
        replit_anthropic_base_url="https://bridge.example.invalid/anthropic",
    )
    report = runtime_report(settings)
    output = json.dumps(report)
    assert "private-sentinel" not in output and "db.example.invalid" not in output
    assert "private-provider-sentinel" not in output and "bridge.example.invalid" not in output
    assert report["provider_requests"] == report["migrations_executed"] == 0
    assert report["deployment_ready"] is False
    assert report["schema"]["status"] == "not_checked"
    assert (
        runtime_report(settings, component="worker")["database_configuration_fingerprint"]
        == report["database_configuration_fingerprint"]
    )
    other = settings.model_copy(update={"database_url": Settings(_env_file=None).database_url})
    assert database_identity(other) != database_identity(settings)


def test_runtime_preflight_reports_production_legacy_as_blocked():
    report = runtime_report(
        Settings(_env_file=None, app_env="production", analysis_model_provider="replit_claude")
    )
    assert report["status"] == "blocked"
    assert "production_requires_scoped_access" in report["blockers"]


def test_runtime_preflight_rejects_invalid_source_policy_without_echoing_contents(tmp_path):
    policy = tmp_path / "invalid-policy.json"
    policy.write_text('{"private-sentinel": "not a permission policy"}')
    settings = Settings(
        _env_file=None, analysis_model_provider="replit_claude", analysis_permissions_path=policy
    )
    report = runtime_report(settings)
    assert report["status"] == "blocked"
    assert "source_policy_valid" in report["blockers"]
    assert "private-sentinel" not in json.dumps(report)


def test_network_launcher_refuses_legacy_access_before_binding(monkeypatch):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts/run_backend.py"
    specification = importlib.util.spec_from_file_location("phase7_run_backend", path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    monkeypatch.setenv("API_ACCESS_MODE", "legacy")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PORT", "8000")

    def forbidden(*args, **kwargs):
        pytest.fail("Legacy access must not bind a network listener")

    monkeypatch.setattr(module.uvicorn, "run", forbidden)
    with pytest.raises(SystemExit, match="scoped access policy"):
        module.main()


def test_runtime_database_receipt_distinguishes_effective_schema_and_host_without_password():
    base = "postgresql+psycopg://operator:private-one@db.example.invalid/fixture"
    first = Settings(_env_file=None, database_url=base)
    password_change = Settings(
        _env_file=None, database_url=base.replace("private-one", "private-two")
    )
    assert database_identity(first) == database_identity(password_change)
    for query in ("?options=-csearch_path%3Done", "?host=other.example.invalid"):
        changed = Settings(_env_file=None, database_url=base + query)
        assert database_identity(first) != database_identity(changed)
    one = Settings(_env_file=None, database_url=base + "?options=-csearch_path%3Done")
    two = Settings(_env_file=None, database_url=base + "?options=-csearch_path%3Dtwo")
    assert database_identity(one) != database_identity(two)


def test_openapi_model_references_operation_ids_and_private_response_headers(database):
    application = create_app(Settings(_env_file=None, app_env="test"), database)
    schema = application.openapi()
    OpenAPI.model_validate(schema)
    operation_ids = []

    def references(value):
        if isinstance(value, dict):
            if "$ref" in value:
                assert value["$ref"].startswith("#/")
                current = schema
                for key in value["$ref"][2:].split("/"):
                    current = current[key.replace("~1", "/").replace("~0", "~")]
            if "operationId" in value:
                operation_ids.append(value["operationId"])
            for item in value.values():
                references(item)
        elif isinstance(value, list):
            for item in value:
                references(item)

    references(schema)
    assert len(operation_ids) == len(set(operation_ids))
    for path in (
        "/api/v1/analyses/{id}",
        "/api/v1/career-analyses/{id}",
        "/api/v1/action-plans/{id}",
    ):
        assert "200" in schema["paths"][path]["get"]["responses"]
    with TestClient(application) as client:
        response = client.get(f"/api/v1/action-plans/{uuid4()}")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
