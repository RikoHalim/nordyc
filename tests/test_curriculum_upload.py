"""Private uploaded curricula; every document below is explicitly synthetic."""

import hashlib
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_curriculum_pdf import _synthetic_pdf

from shiftos.core.config import Settings
from shiftos.main import create_app
from shiftos.models import Course, Document, Institution, Programme, ProgrammeRevision
from shiftos.services.ingestion import uploads, worker
from shiftos.services.ingestion.pdf import detect_brochure_regions


@pytest.fixture
def upload_context(database, tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        curriculum_upload_dir=tmp_path / "private_uploads",
    )
    with database.session_factory() as session:
        institution = Institution(
            name="Synthetic Uploaded University",
            website_url="https://example.invalid",
            is_synthetic=True,
        )
        session.add(institution)
        session.flush()
        programme = Programme(
            institution_id=institution.id,
            name="Synthetic Programme",
            canonical_url="https://example.invalid/programme",
            is_synthetic=True,
        )
        session.add(programme)
        session.commit()
        programme_id = programme.id
    with TestClient(create_app(settings, database)) as client:
        yield client, settings, programme_id


def content():
    return _synthetic_pdf(
        [
            [
                (50, 30, "MAIN COURSES"),
                (50, 60, "YEAR 1"),
                (320, 60, "YEAR 2"),
                (50, 80, "- Synthetic Accounting"),
                (320, 80, "- Synthetic Biology"),
                (50, 200, "ENTRY REQUIREMENTS"),
                (50, 220, "- Not a course"),
            ]
        ]
    )


def upload(context, body=None, **kwargs):
    client, _, programme_id = context
    return client.post(
        f"/api/v1/programmes/{programme_id}/curriculum-pdf",
        content=body or content(),
        headers={"content-type": "application/pdf"},
        **kwargs,
    )


def test_upload_queues_then_worker_imports_and_preserves_original(database, upload_context):
    client, settings, programme_id = upload_context
    response = upload(upload_context)
    assert response.status_code == 202, response.text
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Course)) == 0
    assert worker.run_once(database, settings) == UUID(response.json()["id"])
    job = client.get(f"/api/v1/catalogue/jobs/{response.json()['id']}").json()
    assert job["status"] == "SUCCEEDED", job
    coverage = client.get(f"/api/v1/programmes/{programme_id}/coverage").json()
    assert coverage["course_count"] == 2
    assert coverage["verified_title_count"] == 0
    with database.session_factory() as session:
        documents = session.scalars(select(Document)).all()
        pdf = next(d for d in documents if d.format.value == "PDF")
        assert pdf.content_sha256 == hashlib.sha256(content()).hexdigest()
        assert len(list(settings.curriculum_upload_dir.glob("*.pdf"))) == 1
        assert all(not c.detailed_syllabus_available for c in session.scalars(select(Course)))
    assert upload(upload_context).status_code == 202
    worker.run_once(database, settings)
    assert client.get(f"/api/v1/programmes/{programme_id}/coverage").json()["course_count"] == 2
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ProgrammeRevision)) == 1
        assert session.scalar(select(func.count()).select_from(Document)) == 2


@pytest.mark.parametrize("body", [b"Not a PDF", b"<html>Login</html>"])
def test_invalid_files_are_rejected(upload_context, body):
    assert upload(upload_context, body).status_code == 422


def test_unknown_layout_is_a_visible_failed_job(database, upload_context):
    client, settings, _ = upload_context
    result = upload(upload_context, _synthetic_pdf([[(50, 60, "Synthetic scan substitute")]]))
    assert result.status_code == 202
    worker.run_once(database, settings)
    job = client.get(f"/api/v1/catalogue/jobs/{result.json()['id']}").json()
    assert job["status"] == "FAILED"
    assert "pdf_regions_required" in job["error"]


def test_pdf_storage_failure_cannot_leave_partial_catalogue(database, upload_context, monkeypatch):
    client, settings, programme_id = upload_context
    result = upload(upload_context)

    def fail_anchor(**kwargs):
        raise RuntimeError("Synthetic simulated persistence failure")

    monkeypatch.setattr(uploads, "DocumentAnchor", fail_anchor)
    worker.run_once(database, settings)
    assert client.get(f"/api/v1/catalogue/jobs/{result.json()['id']}").json()["status"] == "FAILED"
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Course)) == 0
        assert session.get(Programme, programme_id).active_revision_id is None


@pytest.mark.parametrize("failure_point", ["coverage", "CatalogueResult"])
def test_upload_result_validation_failure_rolls_back_all_catalogue_records(
    database,
    upload_context,
    monkeypatch,
    failure_point,
):
    client, settings, programme_id = upload_context
    result = upload(upload_context)

    def fail_validation(*args, **kwargs):
        raise ValueError("Synthetic result validation failure")

    monkeypatch.setattr(uploads, failure_point, fail_validation)
    worker.run_once(database, settings)
    assert client.get(f"/api/v1/catalogue/jobs/{result.json()['id']}").json()["status"] == "FAILED"
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Course)) == 0
        assert session.scalar(select(func.count()).select_from(ProgrammeRevision)) == 0
        assert session.scalar(select(func.count()).select_from(Document)) == 0
        assert session.get(Programme, programme_id).active_revision_id is None


def test_upload_requires_existing_write_authorization(database, upload_context):
    _, settings, programme_id = upload_context
    # A fresh configured application exercises the same existing write guard.
    guarded = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        curriculum_upload_dir=settings.curriculum_upload_dir,
        catalogue_write_token="synthetic-secret",
    )
    with TestClient(create_app(guarded, database)) as client:
        assert (
            client.post(
                f"/api/v1/programmes/{programme_id}/curriculum-pdf",
                content=content(),
                headers={"content-type": "application/pdf"},
            ).status_code
            == 401
        )


def test_bad_regions_and_origins_rejected(upload_context):
    assert upload(upload_context, params={"regions": "[]"}).status_code == 422
    assert upload(upload_context, params={"regions": "{}"}).status_code == 422
    assert (
        upload(
            upload_context, params={"source_url": "https://example.invalid:bad/file.pdf"}
        ).status_code
        == 422
    )
    assert (
        upload(upload_context, params={"source_url": "https://other.invalid/file.pdf"}).status_code
        == 422
    )


def test_private_document_integrity_checked_by_worker(database, upload_context):
    client, settings, _ = upload_context
    result = upload(upload_context)
    next(settings.curriculum_upload_dir.glob("*.pdf")).write_bytes(b"changed after upload")
    worker.run_once(database, settings)
    job = client.get(f"/api/v1/catalogue/jobs/{result.json()['id']}").json()
    assert job["status"] == "FAILED"
    assert "UPLOAD_CHECKSUM_MISMATCH" in job["error"]


def test_detector_does_not_invent_regions_without_course_heading():
    from shiftos.services.ingestion.parsers import CurriculumParseError

    with pytest.raises(CurriculumParseError, match="supported"):
        detect_brochure_regions(_synthetic_pdf([[(50, 60, "YEAR 1"), (320, 60, "YEAR 2")]]))


def test_pdf_upload_has_dedicated_bound_and_other_routes_keep_json_bound(upload_context):
    client, _, _ = upload_context
    padded = content() + b" " * 1_100_000
    assert upload(upload_context, padded).status_code == 202
    assert upload(upload_context, b"%PDF-" + b"x" * 20_000_000).status_code == 413
    assert client.post("/api/v1/institutions", content=b"x" * 1_100_000).status_code == 413


def test_upload_contract_exposes_original_pdf_in_openapi(upload_context):
    client, _, _ = upload_context
    operation = client.get("/openapi.json").json()["paths"][
        "/api/v1/programmes/{id}/curriculum-pdf"
    ]["post"]
    assert operation["requestBody"]["content"]["application/pdf"]["schema"]["format"] == "binary"
