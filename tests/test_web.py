"""Real offline worker records behind the optional public read-only boundary."""

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from shiftos.core.config import Settings
from shiftos.main import create_app
from shiftos.models import Course, Institution, Programme, ProgrammeRevision
from shiftos.services.ingestion.worker import run_once
from shiftos.web import WebOptions, create_web_app, deployment_settings

TOKEN = "SYNTHETIC-WEB-READER-TOKEN-NOT-A-LIVE-CREDENTIAL"


@pytest.fixture
def prepared(database, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Web acceptance must not make a provider or research request")

    import httpx

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    source_policy = tmp_path / "source-permissions.private.json"
    source_policy.write_text(json.dumps({"version": "synthetic-web-1", "sources": {}}))
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        analysis_model_provider="replit_claude",
        analysis_write_token="SYNTHETIC-WEB-INTERNAL-ANALYSIS",
        analysis_permissions_path=source_policy,
        analysis_external_processing_allowed=False,
        research_enabled=False,
        gemini_enabled=False,
        analysis_gemini_fallback_enabled=False,
    )
    with database.session_factory() as session:
        institution = Institution(
            name="Fictional public demonstration university", is_synthetic=True
        )
        other = Institution(name="Private unrelated institution", is_synthetic=False)
        session.add_all([institution, other])
        session.flush()
        programme = Programme(
            institution_id=institution.id, name="Fictional one-course review", is_synthetic=True
        )
        session.add(programme)
        session.flush()
        revision = ProgrammeRevision(
            programme_id=programme.id, version_label="synthetic-web-one", is_synthetic=True
        )
        session.add(revision)
        session.flush()
        programme.active_revision_id = revision.id
        course = Course(
            programme_revision_id=revision.id,
            course_name="Synthetic Evidence Practice",
            is_synthetic=True,
        )
        session.add(course)
        session.commit()
        institution_id, programme_id, revision_id, other_id = (
            institution.id,
            programme.id,
            revision.id,
            other.id,
        )
    with TestClient(create_app(settings, database)) as client:
        client.headers["X-Analysis-Token"] = settings.analysis_write_token.get_secret_value()
        analyses = client.post(
            f"/api/v1/programmes/{programme_id}/analyses",
            json={"mode": "offline", "research": False},
        )
        assert analyses.status_code == 202
        run_once(database, settings)
        analysis_id = analyses.json()["id"]
        assert client.get(f"/api/v1/analyses/{analysis_id}").json()["status"] in {
            "SUCCEEDED",
            "PARTIAL",
        }
        careers = client.post(
            f"/api/v1/programmes/{programme_id}/career-analyses", json={"mode": "offline"}
        )
        assert careers.status_code == 202
        run_once(database, settings)
        career_id = careers.json()["id"]
        assert client.get(f"/api/v1/career-analyses/{career_id}").json()["status"] == "PARTIAL"
        plans = client.post(
            f"/api/v1/career-analyses/{career_id}/action-plans",
            json={"mode": "offline", "phase4_analysis_id": analysis_id},
        )
        assert plans.status_code == 202
        run_once(database, settings)
        plan_id = plans.json()["id"]
        assert client.get(f"/api/v1/action-plans/{plan_id}").json()["status"] == "PARTIAL"
    with database.engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version VALUES ('0007_academic_action_plans')")
        )
    access_policy = tmp_path / "access.private.json"
    access_policy.write_text(
        json.dumps(
            {
                "version": "phase7-access-1",
                "principals": [
                    {
                        "principal_id": "synthetic-public-reader",
                        "token_sha256": hashlib.sha256(TOKEN.encode()).hexdigest(),
                        "permissions": ["read"],
                        "institution_ids": [str(institution_id)],
                    }
                ],
            }
        )
    )
    settings = settings.model_copy(
        update={
            "api_access_mode": "scoped",
            "api_access_policy_path": access_policy,
            "analysis_write_token": None,
        }
    )
    dist = tmp_path / "frontend-dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><html><body>SYNTHETIC-BUILT-SPA</body></html>")
    (dist / "assets/app-abcdefgh.js").write_text("console.log('synthetic asset');")
    options = WebOptions(
        dist=dist,
        public_enabled=True,
        public_institution_id=institution_id,
        public_programme_id=programme_id,
        public_principal_id="synthetic-public-reader",
    )
    return SimpleNamespace(
        database=database,
        settings=settings,
        options=options,
        institution_id=institution_id,
        programme_id=programme_id,
        revision_id=revision_id,
        other_id=other_id,
        plan_id=plan_id,
        career_id=career_id,
        analysis_id=analysis_id,
        source_policy=source_policy,
        access_policy=access_policy,
    )


def test_built_spa_has_real_assets_safe_cache_and_protected_api_404(prepared):
    with TestClient(
        create_web_app(prepared.settings, prepared.database, prepared.options)
    ) as client:
        index = client.get(f"/programmes/{prepared.programme_id}/plan")
        assert index.status_code == 200 and "SYNTHETIC-BUILT-SPA" in index.text
        assert index.headers["cache-control"] == "no-store"
        assert index.headers["x-content-type-options"] == "nosniff"
        assert index.headers["x-frame-options"] == "DENY"
        assert client.get("/openapi.json").json()["info"]["title"] == "NORDYC"
        asset = client.get("/assets/app-abcdefgh.js")
        assert asset.status_code == 200 and "immutable" in asset.headers["cache-control"]
        for path in (
            "/api/v1/nonexistent",
            "/api/nonexistent",
            "/api",
            "/.env",
            "/data/private/file.pdf",
            "/assets/%2e%2e/%2e%2e/access.private.json",
            "/assets/missing.js",
        ):
            response = client.get(path)
            assert response.status_code == 404
            assert response.headers["content-type"].startswith("application/json")
            assert "SYNTHETIC-BUILT-SPA" not in response.text


def test_public_reads_are_scoped_and_genuine_saved_results(prepared):
    with TestClient(
        create_web_app(prepared.settings, prepared.database, prepared.options)
    ) as client:
        assert client.get("/__public_demo").json() == {"enabled": True}
        access = client.get("/api/v1/access-context").json()
        assert access["permissions"] == ["read"] and access["global_admin"] is False
        assert access["institution_ids"] == [str(prepared.institution_id)]
        assert client.get("/api/v1/programmes").json()["total"] == 1
        response = client.get(f"/api/v1/action-plans/{prepared.plan_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "PARTIAL" and result["needs_evidence_revalidation"] is False
        assert result["result_json"]["overview"]["course_ids"]
        assert result["result_json"]["is_synthetic"] is True
        assert client.get(f"/api/v1/institutions/{prepared.other_id}").status_code == 404
        assert client.get("/api/v1/sources").status_code == 403
        assert TOKEN not in response.text and "token_sha256" not in response.text


def test_static_assets_refuse_private_files_and_source_maps(prepared):
    for name in ("credential.private.js", "settings.private.json", "app-abcdefgh.js.map"):
        (prepared.options.dist / "assets" / name).write_text("PRIVATE-ASSET-SENTINEL")
    with TestClient(
        create_web_app(prepared.settings, prepared.database, prepared.options)
    ) as client:
        for name in ("credential.private.js", "settings.private.json", "app-abcdefgh.js.map"):
            response = client.get("/assets/" + name)
            assert response.status_code == 404
            assert "PRIVATE-ASSET-SENTINEL" not in response.text


def test_new_deployment_csp_supports_bundled_ajv_without_external_or_inline_scripts(prepared):
    with TestClient(
        create_web_app(prepared.settings, prepared.database, prepared.options)
    ) as client:
        policy = client.get("/").headers["content-security-policy"]
        directives = dict(part.strip().split(" ", 1) for part in policy.split(";") if part.strip())
        assert directives["script-src"] == "'self' 'unsafe-eval'"
        assert "'unsafe-inline'" not in directives["script-src"]
        assert directives["connect-src"] == "'self'"
        assert directives["frame-ancestors"] == "'none'"


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/v1/institutions", {"name": "Must never be created"}),
        ("/api/v1/programmes/{programme}/analyses", {"mode": "live", "research": True}),
        ("/api/v1/programmes/{programme}/curriculum-pdf", None),
        ("/api/v1/action-plans/{plan}/reviews", {"decision": "approved"}),
    ],
)
def test_public_visitors_never_receive_write_or_review_access(prepared, path, body):
    with TestClient(
        create_web_app(prepared.settings, prepared.database, prepared.options)
    ) as client:
        path = path.format(programme=prepared.programme_id, plan=prepared.plan_id)
        response = (
            client.post(path, json=body)
            if body
            else client.post(path, content=b"%PDF-1.4 synthetic")
        )
        assert response.status_code == 401


@pytest.mark.parametrize(
    "header", ["Bearer invalid-supplied-credential-that-is-long-enough", "Basic invalid", ""]
)
def test_supplied_invalid_authorization_is_never_downgraded_to_public(prepared, header):
    with TestClient(
        create_web_app(prepared.settings, prepared.database, prepared.options)
    ) as client:
        assert (
            client.get("/api/v1/programmes", headers={"Authorization": header}).status_code == 401
        )


def test_public_mode_defaults_disabled_and_explicit_auth_still_works(prepared):
    options = replace(prepared.options, public_enabled=False)
    assert WebOptions().public_enabled is False
    with TestClient(create_web_app(prepared.settings, prepared.database, options)) as client:
        assert client.get("/__public_demo").json() == {"enabled": False}
        assert client.get("/api/v1/programmes").status_code == 401
        assert (
            client.get(
                "/api/v1/programmes", headers={"Authorization": "Bearer " + TOKEN}
            ).status_code
            == 200
        )


@pytest.mark.parametrize(
    "change",
    ["real_target", "another_programme", "another_course", "source_policy", "principal_write"],
)
def test_startup_rejects_nonisolated_or_unpermitted_public_state(prepared, change):
    with prepared.database.session_factory() as session:
        if change == "real_target":
            session.get(Institution, prepared.institution_id).is_synthetic = False
        elif change == "another_programme":
            session.add(
                Programme(
                    institution_id=prepared.institution_id,
                    name="Another synthetic programme",
                    is_synthetic=True,
                )
            )
        elif change == "another_course":
            session.add(
                Course(
                    programme_revision_id=prepared.revision_id,
                    course_name="Another fictional course",
                    is_synthetic=True,
                )
            )
        session.commit()
    if change == "source_policy":
        prepared.source_policy.write_text(
            json.dumps({"version": "withdrawn-policy", "sources": {}})
        )
    if change == "principal_write":
        value = json.loads(prepared.access_policy.read_text())
        value["principals"][0]["permissions"].append("write")
        prepared.access_policy.write_text(json.dumps(value))
    with (
        pytest.raises(ValueError),
        TestClient(create_web_app(prepared.settings, prepared.database, prepared.options)),
    ):
        pass


def test_public_access_fails_closed_when_source_permissions_change_after_startup(prepared):
    with TestClient(
        create_web_app(prepared.settings, prepared.database, prepared.options)
    ) as client:
        assert client.get("/api/v1/programmes").status_code == 200
        prepared.source_policy.write_text(json.dumps({"version": "withdrawn-now", "sources": {}}))
        assert client.get("/api/v1/programmes").status_code == 503
        assert client.get("/__public_demo").json() == {"enabled": False}


def test_public_access_fails_closed_on_new_institution_records_after_startup(prepared):
    with TestClient(
        create_web_app(prepared.settings, prepared.database, prepared.options)
    ) as client:
        assert client.get("/api/v1/programmes").status_code == 200
        with prepared.database.session_factory() as session:
            session.add(
                Programme(
                    institution_id=prepared.institution_id,
                    name="Another programme",
                    is_synthetic=True,
                )
            )
            session.commit()
        assert client.get("/api/v1/programmes").status_code == 503


def test_web_startup_requires_existing_migration_head_without_migrating(prepared):
    with prepared.database.engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num='0006_career_alignment'"))
    with (
        pytest.raises(ValueError),
        TestClient(create_web_app(prepared.settings, prepared.database, prepared.options)),
    ):
        pass


def test_web_configuration_rejects_paid_flags_and_malformed_schema(prepared):
    for override in (
        {"analysis_external_processing_allowed": True},
        {"research_enabled": True},
        {"gemini_enabled": True},
        {"analysis_gemini_fallback_enabled": True},
    ):
        with pytest.raises(ValueError):
            create_web_app(
                prepared.settings.model_copy(update=override), prepared.database, prepared.options
            )
    with pytest.raises(ValueError):
        create_web_app(
            prepared.settings,
            prepared.database,
            replace(prepared.options, schema="public; DROP SCHEMA public"),
        )


def test_policy_environment_is_validated_and_materialised_outside_static_assets(monkeypatch):
    value = {
        "version": "phase7-access-1",
        "principals": [
            {
                "principal_id": "synthetic-read",
                "token_sha256": "a" * 64,
                "permissions": ["read"],
                "institution_ids": ["00000000-0000-4000-8000-000000000001"],
            }
        ],
    }
    monkeypatch.setenv("NORDYC_ACCESS_POLICY_JSON", json.dumps(value))
    settings = deployment_settings()
    path = settings.api_access_policy_path
    try:
        assert path is not None and path.name.endswith(".private.json")
        assert json.loads(path.read_text()) == value
        assert "frontend" not in path.parts
    finally:
        if path:
            path.unlink()
            path.parent.rmdir()


def test_optional_worker_uses_normal_existing_worker_and_stops(prepared, monkeypatch):
    import threading

    import shiftos.web as web

    seen = threading.Event()

    def normal(database, settings):
        assert database is prepared.database
        assert settings.analysis_external_processing_allowed is False
        seen.set()

    monkeypatch.setattr(web, "run_once", normal)
    options = replace(prepared.options, worker_enabled=True)
    with TestClient(create_web_app(prepared.settings, prepared.database, options)):
        assert seen.wait(timeout=2)
    assert not any(thread.name == "shiftos-web-worker" for thread in threading.enumerate())


def test_materialised_secret_policy_is_removed_only_after_its_web_lifecycle(prepared, monkeypatch):
    value = json.loads(prepared.access_policy.read_text())
    monkeypatch.setenv("NORDYC_ACCESS_POLICY_JSON", json.dumps(value))
    settings = deployment_settings().model_copy(
        update={
            "app_env": "test",
            "api_access_mode": "scoped",
            "analysis_external_processing_allowed": False,
            "research_enabled": False,
            "gemini_enabled": False,
            "analysis_gemini_fallback_enabled": False,
        }
    )
    path = settings.api_access_policy_path
    assert path and path.is_file()
    with TestClient(
        create_web_app(settings, prepared.database, replace(prepared.options, public_enabled=False))
    ):
        assert path.is_file()
    assert not path.exists()
    assert prepared.access_policy.is_file()


def test_production_factory_can_bootstrap_secret_policy_before_main_import(prepared):
    environment = {
        **os.environ,
        "APP_ENV": "production",
        "API_ACCESS_MODE": "scoped",
        "DATABASE_URL": "postgresql://synthetic@127.0.0.1:1/synthetic_not_connected",
        "NORDYC_ACCESS_POLICY_JSON": prepared.access_policy.read_text(),
        "ANALYSIS_EXTERNAL_PROCESSING_ALLOWED": "false",
        "RESEARCH_ENABLED": "false",
        "GEMINI_ENABLED": "false",
        "ANALYSIS_GEMINI_FALLBACK_ENABLED": "false",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    environment.pop("API_ACCESS_POLICY_PATH", None)
    code = (
        "from pathlib import Path; import socket; "
        "socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('No network')); "
        "from shiftos.web import create_web_app,WebOptions; "
        f"app=create_web_app(options=WebOptions(dist=Path({str(prepared.options.dist)!r}))); "
        "assert app.title=='NORDYC'; "
        "assert app.state.settings.api_access_policy_path.is_file(); "
        "url=app.state.settings.database_url.get_secret_value(); "
        "assert url.startswith('postgresql+psycopg:'); "
        "app.state.database.engine.dispose(); "
        "p=app.state.settings.api_access_policy_path; p.unlink(); p.parent.rmdir()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], env=environment, capture_output=True, timeout=15
    )
    assert result.returncode == 0, "Secret-policy production factory bootstrap failed"
