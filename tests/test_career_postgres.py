"""Real isolated PostgreSQL, worker and protected API; entirely fictional evidence."""

from copy import deepcopy
from uuid import UUID, uuid4

import httpx
import pytest
from career_helpers import TOKEN, career_settings, import_synthetic_taxonomy, seed_career
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker
from test_migrations import migration_database  # noqa: F401 - opt-in PostgreSQL fixture

from alembic import command
from shiftos.db.session import Database
from shiftos.main import create_app
from shiftos.models import (
    CareerRecommendation,
    CareerReview,
    CareerRun,
    Job,
    ProgrammeRevision,
)
from shiftos.services.ingestion.worker import run_once


@pytest.fixture(autouse=True)
def no_live_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Phase 5 PostgreSQL acceptance must never contact an external provider")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def prepared_database(migration_context):
    connection, config = migration_context
    command.upgrade(config, "head")
    connection.commit()
    schema = connection.scalar(text("SELECT current_schema()"))
    connection.commit()
    database = Database(connection.engine, sessionmaker(bind=connection, expire_on_commit=False))
    with database.session_factory() as session:
        fixture = seed_career(session)
    return connection, config, schema, database, fixture


@pytest.mark.integration
def test_career_worker_postgresql_protected_api_reviews_and_independent_commits(
    migration_database,  # noqa: F811
    tmp_path,
):
    connection, _, schema, database, fixture = prepared_database(migration_database)
    imported = import_synthetic_taxonomy(database, fixture, tmp_path)
    assert imported["records_imported"] == 15
    settings = career_settings()
    app = create_app(settings=settings, database=database)
    payload = fixture.request.model_dump(mode="json")
    payload["idempotency_key"] = "synthetic-career-postgresql-1"
    submit = f"/api/v1/programmes/{fixture.programme.id}/career-analyses"
    with TestClient(app) as client:
        assert client.post(submit, json=payload).status_code == 401
        client.headers["X-Analysis-Token"] = TOKEN
        submitted = client.post(submit, json=payload)
        assert submitted.status_code == 202, submitted.text
        queued = submitted.json()
        assert queued["status"] == "QUEUED"
        run_id, job_id = queued["id"], queued["job_id"]
        replay = client.post(submit, json=payload)
        assert replay.status_code == 202 and replay.json()["id"] == run_id
        conflicting = deepcopy(payload)
        conflicting["mappings"] = []
        assert client.post(submit, json=conflicting).status_code == 409
        assert run_once(database, settings) == UUID(job_id)
        completed = client.get(f"/api/v1/career-analyses/{run_id}")
        assert completed.status_code == 200, completed.text
        output = completed.json()
        assert output["status"] in {"SUCCEEDED", "PARTIAL"}
        assert output["fingerprint"] and len(output["fingerprint"]) == 64
        assert output["model_usage_json"]["request_count"] == 0
        assert output["model_name"] is None
        result = output["result_json"]
        assert set(result["course_ids"]) == {str(row.id) for row in fixture.courses.values()}
        assert {row["state"] for row in result["competencies"]} >= {
            "supported",
            "partial",
            "documented_gap",
            "unknown",
        }
        for endpoint, section in (
            ("occupations", "occupations"),
            ("competencies", "competencies"),
            ("evidence", "evidence"),
        ):
            page = client.get(f"/api/v1/career-analyses/{run_id}/{endpoint}")
            assert page.status_code == 200 and page.json()["total"] == len(result[section])
            assert page.json()["items"]
            assert (
                client.get(
                    f"/api/v1/career-analyses/{run_id}/{endpoint}", headers={"X-Analysis-Token": ""}
                ).status_code
                == 401
            )
        recommendation_page = client.get(f"/api/v1/career-analyses/{run_id}/recommendations")
        assert recommendation_page.status_code == 200 and recommendation_page.json()["total"] > 0
        recommendation = recommendation_page.json()["items"][0]
        review_path = f"/api/v1/career-recommendations/{recommendation['id']}/reviews"
        review = {
            "decision": "approved",
            "reason": "Synthetic authenticated review; proposed action only.",
            "expected_recommendation_version": recommendation["version_sha256"],
        }
        assert (
            client.post(review_path, json=review, headers={"X-Analysis-Token": ""}).status_code
            == 401
        )
        assert (
            client.post(
                review_path, json={**review, "expected_recommendation_version": "0" * 64}
            ).status_code
            == 409
        )
        accepted = client.post(review_path, json=review)
        assert accepted.status_code == 201, accepted.text
        assert accepted.json()["actor"] == "authenticated_analysis_operator"
        assert accepted.json()["programme_revision_id"] == str(fixture.revision.id)
        second_review = client.post(
            review_path,
            json={
                **review,
                "decision": "under_review",
                "reason": "Synthetic follow-up academic discussion.",
            },
        )
        assert second_review.status_code == 201
        history = client.get(review_path)
        assert history.status_code == 200 and history.json()["total"] == 2
        assert {row["decision"] for row in history.json()["items"]} == {"approved", "under_review"}
        assert client.get(submit).json()["total"] == 1

        # Withdraw a contributing source: stored historical result remains, but disclosure
        # and fresh approval fail until independently revalidated in a new run.
        with database.session_factory() as session:
            source_version = session.get(type(fixture.version), fixture.version.id)
            source_version.metadata_json = {
                **source_version.metadata_json,
                "rights_withdrawn": True,
            }
            session.commit()
        withheld = client.get(f"/api/v1/career-analyses/{run_id}")
        assert (
            withheld.status_code == 200 and withheld.json()["needs_evidence_revalidation"] is True
        )
        assert withheld.json()["result_json"]["source_text_withheld"] is True
        assert client.get(f"/api/v1/career-analyses/{run_id}/occupations").json()["items"] == []
        assert client.post(review_path, json=review).status_code == 409
        assert client.get(review_path).json()["total"] == 2

    # A new physical PostgreSQL connection must see actual committed rows.
    connection.commit()
    with connection.engine.connect() as independent:
        independent.exec_driver_sql(f'SET search_path TO "{schema}"')
        with sessionmaker(bind=independent)() as session:
            stored = session.get(CareerRun, UUID(run_id))
            assert (
                stored.result_json["competencies"] and stored.fingerprint == output["fingerprint"]
            )
            assert session.scalar(select(func.count()).select_from(CareerRun)) == 1
            assert (
                session.scalar(select(func.count()).select_from(CareerRecommendation))
                == recommendation_page.json()["total"]
            )
            assert session.scalar(select(func.count()).select_from(CareerReview)) == 2
            job = session.get(Job, UUID(job_id))
            assert job.status.value in {"SUCCEEDED", "PARTIAL"} and job.completed_at
    assert run_once(database, settings) is None


@pytest.mark.integration
def test_career_postgresql_composite_ownership_append_only_and_loss_prevention(migration_database):  # noqa: F811
    connection, config, _, database, fixture = prepared_database(migration_database)
    settings = career_settings()
    with TestClient(create_app(settings=settings, database=database)) as client:
        client.headers["X-Analysis-Token"] = TOKEN
        submitted = client.post(
            f"/api/v1/programmes/{fixture.programme.id}/career-analyses",
            json=fixture.request.model_dump(mode="json"),
        )
        assert submitted.status_code == 202, submitted.text
        run_id, job_id = UUID(submitted.json()["id"]), UUID(submitted.json()["job_id"])
        assert run_once(database, settings) == job_id
        page = client.get(f"/api/v1/career-analyses/{run_id}/recommendations")
        recommendation = page.json()["items"][0]
        accepted = client.post(
            f"/api/v1/career-recommendations/{recommendation['id']}/reviews",
            json={
                "decision": "approved",
                "reason": "Synthetic immutable review.",
                "expected_recommendation_version": recommendation["version_sha256"],
            },
        )
        assert accepted.status_code == 201, accepted.text
        review_id = UUID(accepted.json()["id"])
    connection.commit()
    # DB triggers cover direct SQL writes, not only SQLAlchemy mapper events.
    for table, record_id, column, value in (
        ("career_recommendations", UUID(recommendation["id"]), "recommendation_key", "changed"),
        ("career_reviews", review_id, "reason", "changed"),
        ("career_runs", run_id, "mode", "live"),
    ):
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(f"UPDATE {table} SET {column} = :value WHERE id = :id"),
                {"value": value, "id": record_id},
            )
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": record_id})
    with database.session_factory() as session:
        new_revision = ProgrammeRevision(
            id=uuid4(),
            programme_id=fixture.programme.id,
            version_label="synthetic-unrelated-version",
            is_synthetic=True,
        )
        session.add(new_revision)
        session.commit()
        wrong_revision = new_revision.id
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(
            CareerRecommendation.__table__.insert().values(
                id=uuid4(),
                run_id=run_id,
                programme_revision_id=wrong_revision,
                recommendation_key="synthetic-wrong-revision",
                version_sha256="0" * 64,
                result_json={},
                is_synthetic=True,
            )
        )
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(
            CareerReview.__table__.insert().values(
                id=uuid4(),
                recommendation_id=UUID(recommendation["id"]),
                run_id=run_id,
                programme_revision_id=fixture.revision.id,
                recommendation_version="0" * 64,
                actor="authenticated_analysis_operator",
                decision="approved",
                reason="Synthetic wrong-version direct SQL must fail the composite foreign key.",
                reviewed_at=fixture.now,
                is_synthetic=True,
            )
        )
    connection.commit()
    with pytest.raises(RuntimeError, match="Career|career|Phase 5|Phase5"):
        command.downgrade(config, "0005_programme_analysis")
    connection.rollback()
    assert connection.scalar(text("SELECT count(*) FROM career_runs")) == 1
    assert connection.scalar(text("SELECT count(*) FROM career_reviews")) == 1
