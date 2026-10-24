"""Owned private preview infrastructure; provider traffic is never permitted."""

import hashlib
import http.client
import importlib.util
import json
import os
import socket
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID

import httpx
import pytest
import uvicorn
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from test_curriculum_upload import content as fictional_pdf

from shiftos.core.access import AccessPolicy
from shiftos.models import Course, Job

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "synthetic_preview_runner", ROOT / "scripts" / "preview_synthetic.py"
)
preview_runner = importlib.util.module_from_spec(_spec)
# dataclasses resolves the defining module while constructing its class.
import sys  # noqa: E402

sys.modules[_spec.name] = preview_runner
_spec.loader.exec_module(preview_runner)


@pytest.mark.parametrize(
    "value",
    [
        "sqlite+pysqlite:///:memory:",
        "postgresql://operator@remote.invalid/shiftos_test",
        "postgresql://operator@127.0.0.1/shiftos_production",
        "postgresql://operator@127.0.0.1/shiftos_test?options=-csearch_path=public",
    ],
)
def test_preview_refuses_ambient_shared_or_non_postgresql_targets(value):
    with pytest.raises(ValueError, match="owned loopback PostgreSQL"):
        preview_runner.validate_database_url(value)


def test_preview_credentials_are_private_random_scoped_and_hashed(tmp_path):
    institution = "c161e45e-40ac-4baa-bb57-70bf6e5a6841"
    credentials = preview_runner.issue_access(tmp_path, [institution])
    policy_text = (tmp_path / "access-policy.private.json").read_text()
    policy = AccessPolicy.model_validate_json(policy_text)
    assert len(policy.principals) == 4
    assert len({row["token"].get_secret_value() for row in credentials.values()}) == 4
    for alias, entry in credentials.items():
        private_token = entry["token"].get_secret_value()
        assert len(private_token) >= 32 and private_token not in policy_text
        assert private_token not in repr(entry)
        principal = next(row for row in policy.principals if row.principal_id.endswith(alias))
        assert principal.token_sha256 == hashlib.sha256(private_token.encode()).hexdigest()
    assert credentials["reader"]["permissions"] == ["read"]
    assert credentials["operator"]["institution_ids"] == [institution]
    assert institution not in credentials["foreign"]["institution_ids"]
    if os.name != "nt":
        assert (tmp_path / "auth.private.json").stat().st_mode & 0o077 == 0


def test_preview_settings_cannot_inherit_real_provider_keys(monkeypatch, tmp_path):
    for variable in ("AI_INTEGRATIONS_ANTHROPIC_API_KEY", "GEMINI_API_KEY", "BRAVE_SEARCH_API_KEY"):
        monkeypatch.setenv(variable, "SYNTHETIC-UNUSABLE-ENVIRONMENT-SENTINEL")
    monkeypatch.setenv("API_ACCESS_MODE", "scoped")
    settings = preview_runner.preview_settings(
        "postgresql+psycopg://operator@127.0.0.1/shiftos_test", tmp_path
    )
    assert settings.api_access_mode == "legacy"
    assert settings.gemini_api_key is settings.brave_search_api_key is None
    assert settings.replit_anthropic_api_key is settings.replit_anthropic_base_url is None
    assert not settings.gemini_enabled and not settings.analysis_gemini_fallback_enabled
    assert not settings.research_enabled and not settings.discovery_enabled
    with preview_runner.preview_mocked_workers():
        with pytest.raises(RuntimeError, match="Real HTTP is prohibited"):
            httpx.get("https://example.invalid/no-network", timeout=0.1)
        with pytest.raises(RuntimeError, match="External HTTP is prohibited"):
            http.client.HTTPSConnection("example.invalid", timeout=0.1).connect()


def test_preview_private_paths_and_network_binding_fail_closed(tmp_path):
    allowed = tmp_path / "ignored"
    assert preview_runner.private_directory(allowed / "preview", allowed_root=allowed).is_dir()
    with pytest.raises(ValueError, match="inside this checkout"):
        preview_runner.private_directory(tmp_path / "outside", allowed_root=allowed)
    with pytest.raises(ValueError, match="literal loopback"):
        preview_runner.serve_preview(None, host="0.0.0.0")
    with pytest.raises(ValueError, match="without a preview owner"):
        preview_runner.drop_owned_schema(None, "public", preview_runner.OWNER_PREFIX + "x")


def _http(origin, path, token=None, *, body=None, content_type="application/json"):
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = "Bearer " + token
    payload = (
        body if isinstance(body, bytes) else json.dumps(body).encode() if body is not None else None
    )
    request = Request(origin + path, data=payload, headers=headers)
    try:
        with urlopen(request, timeout=8) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def _wait_job(origin, job_id, token):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        status, job = _http(origin, f"/api/v1/catalogue/jobs/{job_id}", token)
        assert status == 200
        if job["status"] not in {"QUEUED", "RUNNING"}:
            return job
        time.sleep(0.05)
    pytest.fail("The real preview worker did not finish its committed job")


@pytest.mark.integration
def test_preview_real_http_worker_pdf_and_independent_postgresql(tmp_path):
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set TEST_DATABASE_URL to verify the owned PostgreSQL browser preview")
    preview_runner.validate_database_url(value)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    run_dir = tmp_path / "preview"
    schema = None
    with preview_runner.synthetic_preview(
        value, run_dir, disciplines=("computing", "accounting", "biotechnology")
    ) as preview:
        schema = preview.receipt["database"]["schema"]
        assert len(preview.reports) == 3
        assert all(report["persistence"]["postgresql_verified"] for report in preview.reports)
        origin = f"http://127.0.0.1:{port}"
        server = uvicorn.Server(
            uvicorn.Config(
                preview.app, host="127.0.0.1", port=port, log_level="error", access_log=False
            )
        )
        thread = threading.Thread(target=server.run)
        thread.start()
        try:
            deadline = time.monotonic() + 8
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started
            operator = preview.credentials["operator"]["token"].get_secret_value()
            reader = preview.credentials["reader"]["token"].get_secret_value()
            foreign = preview.credentials["foreign"]["token"].get_secret_value()
            assert _http(origin, "/api/v1/programmes")[0] == 401
            status, page = _http(origin, "/api/v1/programmes", operator)
            assert status == 200 and page["total"] == 3
            programme = page["items"][0]
            programme_id = programme["id"]
            assert _http(origin, "/api/v1/programmes", foreign)[1]["total"] == 0
            assert _http(origin, f"/api/v1/programmes/{programme_id}", foreign)[0] == 404
            assert (
                _http(
                    origin,
                    f"/api/v1/programmes/{programme_id}/analyses",
                    reader,
                    body={"mode": "offline", "research": False},
                )[0]
                == 403
            )
            status, queued = _http(
                origin,
                f"/api/v1/programmes/{programme_id}/curriculum-pdf",
                operator,
                body=fictional_pdf(),
                content_type="application/pdf",
            )
            assert status == 202 and queued["status"] in {"QUEUED", "RUNNING"}
            job = _wait_job(origin, queued["id"], operator)
            assert job["status"] == "SUCCEEDED", job
            status, courses = _http(origin, f"/api/v1/programmes/{programme_id}/courses", operator)
            assert status == 200 and courses["total"] == 2
            assert all(row["evidence_level"] == "title_only" for row in courses["items"])
            status, analysis = _http(
                origin,
                f"/api/v1/programmes/{programme_id}/analyses",
                operator,
                body={"mode": "offline", "research": False},
            )
            assert status == 202
            completed = _wait_job(origin, analysis["job_id"], operator)
            assert completed["status"] in {"SUCCEEDED", "PARTIAL"}
            status, findings = _http(origin, f"/api/v1/analyses/{analysis['id']}/courses", operator)
            assert status == 200 and findings["total"] == 2
            with preview.database.engine.connect() as independent:
                assert independent.scalar(text("SELECT current_schema()")) == schema
                row = independent.execute(
                    select(Job.status).where(Job.id == UUID(queued["id"]))
                ).scalar_one()
                assert row.value == "SUCCEEDED"
                assert (
                    len(
                        independent.execute(
                            select(Course.id).where(
                                Course.programme_revision_id
                                == UUID(courses["programme_revision_id"])
                            )
                        ).all()
                    )
                    == 2
                )
            assert preview.worker.completed_jobs >= 2
            assert preview.receipt["live_requests"] == 0
            for grant in preview.credentials.values():
                assert (
                    grant["token"].get_secret_value() not in (run_dir / "receipt.json").read_text()
                )
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive()
    assert not (run_dir / "auth.private.json").exists()
    receipt = json.loads((run_dir / "receipt.json").read_text())
    assert receipt["database"]["cleanup"] == "removed_owned_schema"
    engine = preview_runner.create_engine(make_url(value))
    try:
        with engine.connect() as connection:
            assert not connection.scalar(
                text("SELECT 1 FROM pg_namespace WHERE nspname=:s"), {"s": schema}
            )
    finally:
        engine.dispose()
