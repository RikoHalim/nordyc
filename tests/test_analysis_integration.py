"""PostgreSQL worker/API proof over three invented disciplines, with providers forbidden."""

import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from test_migrations import migration_database  # noqa: F401 - isolated PostgreSQL fixture

from alembic import command
from shiftos.api.routers.analysis import router
from shiftos.core.config import Settings
from shiftos.db.session import Database
from shiftos.main import create_app
from shiftos.models import (
    AnalysisRun,
    Course,
    CourseFinding,
    Institution,
    Programme,
    ProgrammeRevision,
)
from shiftos.services.ingestion.worker import run_once


@pytest.mark.integration
@pytest.mark.parametrize("discipline", ["computing", "accounting", "marine_biotechnology"])
def test_postgresql_analysis_queue_worker_all_courses_and_authorized_reads(
    migration_database,  # noqa: F811 - imported fixture
    tmp_path,
    monkeypatch,
    discipline,
):
    connection, config = migration_database
    command.upgrade(config, "head")
    connection.commit()
    database = Database(connection.engine, sessionmaker(bind=connection, expire_on_commit=False))
    policy = tmp_path / "permissions.synthetic.json"
    policy.write_text(json.dumps({"version": "synthetic-test-1", "sources": {}}), encoding="utf-8")
    settings = Settings(
        _env_file=None,
        app_env="test",
        analysis_write_token="synthetic-pg-analysis-token",
        analysis_permissions_path=policy,
    )
    with database.session_factory() as session:
        institution = Institution(
            name="Synthetic PostgreSQL Analysis University", is_synthetic=True
        )
        session.add(institution)
        session.flush()
        programme = Programme(
            institution_id=institution.id,
            name=f"Synthetic {discipline} programme",
            discipline_key=discipline,
            is_synthetic=True,
        )
        session.add(programme)
        session.flush()
        revision = ProgrammeRevision(
            programme_id=programme.id,
            version_label="synthetic-pg-analysis-v1",
            is_synthetic=True,
        )
        session.add(revision)
        session.flush()
        programme.active_revision_id = revision.id
        courses = [
            Course(
                programme_revision_id=revision.id,
                course_name=f"Synthetic {discipline} course {index}",
                year=index + 1,
                is_synthetic=True,
            )
            for index in range(3)
        ]
        session.add_all(courses)
        session.commit()
        programme_id, revision_id = programme.id, revision.id
        course_ids = {str(course.id) for course in courses}

    from shiftos.services.analysis.providers import BraveSearch, GeminiProvider

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline integration must not call search or model providers")

    monkeypatch.setattr(GeminiProvider, "generate", forbidden)
    monkeypatch.setattr(BraveSearch, "search", forbidden)
    app = create_app(settings=settings, database=database)
    if not any(getattr(route, "path", None) == "/api/v1/analyses/{id}" for route in app.routes):
        app.include_router(router)
    with TestClient(app) as client:
        client.headers["X-Analysis-Token"] = "synthetic-pg-analysis-token"
        submission_path = f"/api/v1/programmes/{programme_id}/analyses"
        payload = {"mode": "offline", "idempotency_key": "synthetic-pg-repeat"}
        queued = client.post(submission_path, json=payload)
        assert queued.status_code == 202, queued.text
        run_id, job_id = queued.json()["id"], queued.json()["job_id"]
        assert queued.json()["status"] == "QUEUED"
        assert queued.json()["programme_revision_id"] == str(revision_id)
        assert client.get(f"/api/v1/analyses/{run_id}/courses").json()["total"] == 0
        assert run_once(database, settings) == UUID(job_id)
        response = client.get(f"/api/v1/analyses/{run_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "SUCCEEDED", result
        assert result["summary_json"]["result_mode"] == "offline_synthetic"
        assert result["summary_json"]["summary"]["inventory_count"] == 3
        assert result["summary_json"]["summary"]["returned_count"] == 3
        assert result["is_synthetic"] is True
        assert result["model_name"] is None
        assert len(result["fingerprint"]) == 64
        findings = client.get(f"/api/v1/analyses/{run_id}/courses").json()
        assert findings["total"] == 3
        assert {row["course_id"] for row in findings["items"]} == course_ids
        assert all(
            row["result_json"]["is_final_curriculum_verdict"] is False for row in findings["items"]
        )
        assert all(
            row["result_json"]["needs_syllabus_confirmation"] is True for row in findings["items"]
        )
        assert (
            client.get(f"/api/v1/analyses/{run_id}/courses?limit=1&offset=1").json()["total"] == 3
        )
        first = findings["items"][0]
        detail = client.get(f"/api/v1/analyses/{run_id}/courses/{first['course_id']}")
        assert detail.status_code == 200 and detail.json() == first
        assert client.get(f"/api/v1/analyses/{run_id}/courses/{uuid4()}").status_code == 404
        assert (
            client.get(
                f"/api/v1/catalogue/jobs/{job_id}", headers={"X-Analysis-Token": ""}
            ).status_code
            == 401
        )
        assert client.get(submission_path).json()["total"] == 1
        assert client.post(submission_path, json=payload).json()["id"] == run_id
        assert run_once(database, settings) is None
        assert (
            client.get(f"/api/v1/analyses/{run_id}").json()["fingerprint"] == result["fingerprint"]
        )
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(AnalysisRun)) == 1
        assert session.scalar(select(func.count()).select_from(CourseFinding)) == 3
