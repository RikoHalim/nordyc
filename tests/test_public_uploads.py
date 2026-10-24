"""Bounded public upload capabilities; all documents here are fictional fixtures."""

import json
from dataclasses import replace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_curriculum_pdf import _synthetic_pdf
from test_web import prepared  # noqa: F401 - real one-course offline saved-result fixture

from shiftos import public_uploads
from shiftos.models import Job
from shiftos.services.ingestion.worker import run_once
from shiftos.web import WebWorker, create_web_app

ORIGIN = {"Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"}
PAYLOAD = {
    "institution_name": "User-attributed public example university",
    "institution_url": "https://public-curriculum.example.invalid/",
    "programme_name": "User-attributed programme",
    "programme_url": "https://public-curriculum.example.invalid/programme",
    "permitted_public_document": True,
}


@pytest.fixture
def uploads(prepared, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("SESSION_SECRET", "SYNTHETIC-TEST-SESSION-SECRET-NEVER-A-LIVE-KEY")
    monkeypatch.delenv("NORDYC_UPLOAD_SESSION_SECRET", raising=False)
    monkeypatch.setattr(WebWorker, "start", lambda self: None)
    monkeypatch.setattr(WebWorker, "close", lambda self: None)
    prepared.settings = prepared.settings.model_copy(
        update={"curriculum_upload_dir": tmp_path / "private-uploads"}
    )
    prepared.options = replace(prepared.options, public_uploads_enabled=True)
    return prepared


def bootstrap(client):
    response = client.post("/__public_upload_session", json=PAYLOAD, headers=ORIGIN)
    assert response.status_code == 201, response.text
    return response


def test_session_isolated_user_attributed_not_synthetic_and_cookie_is_http_only(uploads):
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        response = bootstrap(client)
        assert (
            "HttpOnly" in response.headers["set-cookie"]
            and "SameSite=strict" in response.headers["set-cookie"]
        )
        assert public_uploads.COOKIE not in response.text
        value = response.json()
        assert value["institution_id"] != str(uploads.institution_id)
        assert value["programme_id"] != str(uploads.programme_id)
        assert (
            client.get("/__public_demo").json()["upload_institution_id"] == value["institution_id"]
        )
        access = client.get("/api/v1/access-context").json()
        assert set(access["permissions"]) == {"read", "write"}
        assert set(access["institution_ids"]) == {
            value["institution_id"],
            str(uploads.institution_id),
        }
        programme = client.get(f"/api/v1/programmes/{value['programme_id']}").json()
        assert programme["is_synthetic"] is False and programme["active_revision_id"] is None
        assert (
            client.post("/__public_upload_session", json=PAYLOAD, headers=ORIGIN).status_code == 200
        )


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/v1/institutions", {"name": "No admin"}),
        ("/api/v1/programmes/{seed}/curriculum-pdf", None),
        ("/api/v1/programmes/{seed}/analyses", {"mode": "offline", "research": False}),
        ("/api/v1/action-plans/{plan}/reviews", {"decision": "approved"}),
        ("/api/v1/catalogue/discover", {"provider": "xmum"}),
    ],
)
def test_session_never_writes_saved_example_reviews_admin_or_discovery(uploads, path, body):
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        bootstrap(client)
        path = path.format(seed=uploads.programme_id, plan=uploads.plan_id)
        response = (
            client.post(path, json=body, headers=ORIGIN)
            if body is not None
            else client.post(
                path,
                content=b"%PDF-1.4 fictional",
                headers={**ORIGIN, "Content-Type": "application/pdf"},
            )
        )
        assert response.status_code == 403
        assert client.get("/api/v1/sources").status_code == 403


@pytest.mark.parametrize(
    "mode,research,extra",
    [
        ("live", False, {}),
        ("offline", True, {}),
        ("offline", False, {"as_of": "2026-10-20T00:00:00Z"}),
    ],
)
def test_paid_or_advanced_analysis_inputs_are_rejected_before_job_creation(
    uploads, mode, research, extra
):
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        own = bootstrap(client).json()
        result = client.post(
            f"/api/v1/programmes/{own['programme_id']}/analyses",
            json={"mode": mode, "research": research, **extra},
            headers=ORIGIN,
        )
        assert result.status_code == 403
    with uploads.database.session_factory() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Job)
                .where(
                    Job.institution_id == UUID(own["institution_id"]),
                    Job.kind == "PROGRAMME_ANALYSIS",
                )
            )
            == 0
        )


def test_distinct_judges_cannot_read_or_write_each_others_programmes(uploads):
    app = create_web_app(uploads.settings, uploads.database, uploads.options)
    with TestClient(app) as first, TestClient(app) as second:
        a, b = bootstrap(first).json(), bootstrap(second).json()
        assert a["institution_id"] != b["institution_id"]
        assert first.get(f"/api/v1/programmes/{b['programme_id']}").status_code == 404
        assert second.get(f"/api/v1/programmes/{a['programme_id']}").status_code == 404
        assert (
            first.post(
                f"/api/v1/programmes/{b['programme_id']}/curriculum-pdf",
                content=b"%PDF-1.4 test",
                headers={**ORIGIN, "Content-Type": "application/pdf"},
            ).status_code
            == 403
        )


def test_forged_cookie_invalid_bearer_and_foreign_origins_never_gain_access(uploads):
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        own = bootstrap(client).json()
        assert (
            client.post(
                f"/api/v1/programmes/{own['programme_id']}/analyses",
                json={"mode": "offline", "research": False},
                headers={"Origin": "https://evil.invalid"},
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/v1/programmes",
                headers={"Authorization": "Bearer wrong-credential-that-is-long-enough"},
            ).status_code
            == 401
        )
        cookie = client.cookies.get(public_uploads.COOKIE)
        client.cookies.clear()
        client.cookies.set(public_uploads.COOKIE, cookie + "forged")
        assert client.get(f"/api/v1/programmes/{own['programme_id']}").status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("institution_name", "  "),
        ("programme_url", "https://user:secret@example.org/programme"),
        ("institution_url", "http://example.org"),
        ("programme_url", "https://127.0.0.1/programme"),
        ("programme_url", "https://localhost/programme"),
        ("permitted_public_document", False),
    ],
)
def test_unattributed_private_or_unconsented_metadata_is_rejected(uploads, field, value):
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        response = client.post(
            "/__public_upload_session", json={**PAYLOAD, field: value}, headers=ORIGIN
        )
        assert response.status_code == 422
        assert "user:secret" not in response.text


def test_durable_upload_reservations_limit_parallel_attempts_and_survive_factory_restart(uploads):
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        own = bootstrap(client).json()
        # Invalid documents still consume a bounded attempt, preventing a race
        # or deliberately failing parser from obtaining unlimited processing.
        path = f"/api/v1/programmes/{own['programme_id']}/curriculum-pdf"
        for _ in range(3):
            assert (
                client.post(
                    path, content=b"bad", headers={**ORIGIN, "Content-Type": "application/pdf"}
                ).status_code
                == 422
            )
        cookie = client.cookies.get(public_uploads.COOKIE)
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        client.cookies.set(public_uploads.COOKIE, cookie)
        assert (
            client.post(
                path,
                content=b"%PDF-1.4 fictional",
                headers={**ORIGIN, "Content-Type": "application/pdf"},
            ).status_code
            == 429
        )


def test_expired_session_and_changed_example_permissions_fail_closed(uploads):
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        own = bootstrap(client).json()
        uploads.source_policy.write_text(json.dumps({"version": "withdrawn", "sources": {}}))
        assert client.get(f"/api/v1/programmes/{own['programme_id']}").status_code == 503


def test_actual_private_pdf_queues_and_extracts_only_in_its_upload_tenant(uploads):
    content = _synthetic_pdf(
        [
            [
                (50, 10, "Entirely fictional public upload test"),
                (50, 30, "MAIN COURSES"),
                (50, 60, "Year 1"),
                (50, 80, "- Synthetic Evidence Practice"),
                (330, 60, "Year 2"),
                (330, 80, "- Synthetic Inquiry"),
            ]
        ]
    )
    with TestClient(create_web_app(uploads.settings, uploads.database, uploads.options)) as client:
        own = bootstrap(client).json()
        queued = client.post(
            f"/api/v1/programmes/{own['programme_id']}/curriculum-pdf",
            content=content,
            headers={**ORIGIN, "Content-Type": "application/pdf"},
        )
        assert queued.status_code == 202, queued.text
        assert run_once(
            uploads.database,
            uploads.settings,
            allowed_kinds=public_uploads.PUBLIC_JOB_KINDS,
            institution_ids={UUID(own["institution_id"])},
            offline_analysis_only=True,
        ) == UUID(queued.json()["id"])
        job = client.get(f"/api/v1/catalogue/jobs/{queued.json()['id']}").json()
        assert job["status"] in {"SUCCEEDED", "PARTIAL"}, job
        programme = client.get(f"/api/v1/programmes/{own['programme_id']}").json()
        assert programme["active_revision_id"]
        courses = client.get(f"/api/v1/programmes/{own['programme_id']}/courses").json()
        assert courses["total"] == 2
        assert all(
            row["is_synthetic"] is False and row["is_verified"] is False for row in courses["items"]
        )
        assert not list((uploads.options.dist).rglob("*.pdf"))


def test_upload_enable_requires_public_mode_and_persistent_secret(uploads, monkeypatch):
    monkeypatch.delenv("SESSION_SECRET")
    with pytest.raises(ValueError):
        create_web_app(uploads.settings, uploads.database, uploads.options)
    with pytest.raises(ValueError):
        create_web_app(
            uploads.settings, uploads.database, replace(uploads.options, public_enabled=False)
        )
