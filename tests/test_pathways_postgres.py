"""Real isolated PostgreSQL action plans; model/research traffic is prohibited."""

from copy import deepcopy
from uuid import UUID, uuid4

import httpx
import pytest
from career_helpers import TOKEN
from fastapi.testclient import TestClient
from pathways_helpers import seed_pathways
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker
from test_migrations import migration_database  # noqa: F401 - isolated PostgreSQL fixture

from alembic import command
from shiftos.db.session import Database
from shiftos.main import create_app
from shiftos.models import ActionPlanReview, ActionPlanRun, Job, PlanRecommendation
from shiftos.services.ingestion.worker import run_once


@pytest.fixture(autouse=True)
def no_live_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Phase 6 PostgreSQL tests must not make live model, search or source calls")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def prepare(context):
    connection, config = context
    command.upgrade(config, "head")
    connection.commit()
    schema = connection.scalar(text("SELECT current_schema()"))
    connection.commit()
    database = Database(connection.engine, sessionmaker(bind=connection, expire_on_commit=False))
    with database.session_factory() as session:
        fixture = seed_pathways(session, database)
    return connection, config, schema, database, fixture


def submit_complete(client, database, fixture):
    body = fixture.request.model_dump(mode="json")
    body["idempotency_key"] = "synthetic-pathways-postgresql-1"
    submit_path = f"/api/v1/career-analyses/{fixture.parent.id}/action-plans"
    queued = client.post(submit_path, json=body)
    assert queued.status_code == 202, queued.text
    result = queued.json()
    assert result["status"] == "QUEUED"
    assert run_once(database, fixture.settings) == UUID(result["job_id"])
    completed = client.get(f"/api/v1/action-plans/{result['id']}")
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] in {"SUCCEEDED", "PARTIAL"}, completed.text
    return submit_path, body, result, completed.json()


@pytest.mark.integration
def test_action_plan_worker_protected_results_official_sdgs_review_and_independent_pg(
    migration_database,  # noqa: F811
):
    connection, _, schema, database, fixture = prepare(migration_database)
    assert fixture.sdg_report["status"] == "SUCCEEDED"
    assert fixture.sdg_report["records_imported"] == 186
    with TestClient(create_app(settings=fixture.settings, database=database)) as client:
        submission = f"/api/v1/career-analyses/{fixture.parent.id}/action-plans"
        assert (
            client.post(submission, json=fixture.request.model_dump(mode="json")).status_code == 401
        )
        client.headers["X-Analysis-Token"] = TOKEN
        submit_path, body, queued, complete = submit_complete(client, database, fixture)
        run_id, job_id = UUID(queued["id"]), UUID(queued["job_id"])
        assert complete["career_run_id"] == str(fixture.parent.id)
        assert complete["career_fingerprint"] == fixture.parent.fingerprint
        assert (
            len(complete["fingerprint"]) == 64
            and complete["model_usage_json"]["request_count"] == 0
        )
        result = complete["result_json"]
        assert result["is_synthetic"] is True
        assert len(result["overview"]["course_ids"]) == 4
        assert len(result["career"]["occupations"]) == 3
        assert len(result["pathways"]) >= 2 and len(result["scenarios"]) == 2
        assert (
            sum(row["status"] == "possible_contribution" for row in result["sdg_alignments"]) == 2
        )
        replay = client.post(submit_path, json=body)
        assert replay.status_code == 202 and replay.json()["id"] == str(run_id)
        conflicting = deepcopy(body)
        conflicting["durations"] = []
        assert client.post(submit_path, json=conflicting).status_code == 409
        for route, field in (
            ("pathways", "pathways"),
            ("resources", "resources"),
            ("scenarios", "scenarios"),
            ("sdg", "sdg_alignments"),
            ("evidence", "evidence"),
        ):
            path = f"/api/v1/action-plans/{run_id}/{route}"
            assert client.get(path, headers={"X-Analysis-Token": ""}).status_code == 401
            page = client.get(path)
            assert page.status_code == 200 and page.json()["total"] == len(result[field])
            assert page.json()["items"]
        pathway = result["pathways"][0]
        steps = client.get(f"/api/v1/action-plans/{run_id}/pathways/{pathway['key']}/steps")
        assert steps.status_code == 200 and steps.json()["total"] == len(pathway["steps"])
        comparison = client.get(f"/api/v1/action-plans/{run_id}/comparison")
        assert (
            comparison.status_code == 200
            and comparison.json()["comparison"] == result["comparison"]
        )
        review_path = f"/api/v1/action-plans/{run_id}/reviews"
        review = {
            "decision": "under_review",
            "reason": "Fictional authenticated review; no named academic identity claimed.",
            "expected_plan_fingerprint": complete["fingerprint"],
        }
        assert (
            client.post(review_path, json=review, headers={"X-Analysis-Token": ""}).status_code
            == 401
        )
        assert (
            client.post(
                review_path, json={**review, "expected_plan_fingerprint": "0" * 64}
            ).status_code
            == 409
        )
        recorded = client.post(review_path, json=review)
        assert recorded.status_code == 201, recorded.text
        assert recorded.json()["actor"] == "authenticated_analysis_operator"
        assert client.get(review_path).json()["total"] == 1
        assert client.get(submit_path).json()["total"] == 1
        with database.session_factory() as session:
            source_version = session.get(
                type(fixture.resource_versions["model-workbook"]),
                fixture.resource_versions["model-workbook"].id,
            )
            source_version.metadata_json = {
                **source_version.metadata_json,
                "rights_withdrawn": True,
            }
            session.commit()
        withheld = client.get(f"/api/v1/action-plans/{run_id}")
        assert (
            withheld.status_code == 200 and withheld.json()["needs_evidence_revalidation"] is True
        )
        assert withheld.json()["result_json"]["source_text_withheld"] is True
        assert client.get(f"/api/v1/action-plans/{run_id}/resources").json()["items"] == []
        assert client.post(review_path, json={**review, "decision": "approved"}).status_code == 409
        assert client.get(review_path).json()["total"] == 1
    connection.commit()
    with connection.engine.connect() as independent:
        independent.exec_driver_sql(f'SET search_path TO "{schema}"')
        with sessionmaker(bind=independent)() as session:
            stored = session.get(ActionPlanRun, run_id)
            assert stored.fingerprint == complete["fingerprint"] and stored.result_json == result
            assert session.scalar(select(func.count()).select_from(PlanRecommendation)) == 5
            assert session.scalar(select(func.count()).select_from(ActionPlanReview)) == 1
            assert session.get(Job, job_id).completed_at
    assert run_once(database, fixture.settings) is None


@pytest.mark.integration
def test_plan_postgresql_exact_parent_bindings_immutable_history_and_safe_downgrade(
    migration_database,  # noqa: F811
):
    connection, config, _, database, fixture = prepare(migration_database)
    with TestClient(create_app(settings=fixture.settings, database=database)) as client:
        client.headers["X-Analysis-Token"] = TOKEN
        _, _, queued, complete = submit_complete(client, database, fixture)
        run_id = UUID(queued["id"])
        revision_id = UUID(complete["programme_revision_id"])
        review = client.post(
            f"/api/v1/action-plans/{run_id}/reviews",
            json={
                "decision": "under_review",
                "reason": "Synthetic immutable plan review.",
                "expected_plan_fingerprint": complete["fingerprint"],
            },
        )
        assert review.status_code == 201, review.text
        review_id = UUID(review.json()["id"])
    connection.commit()
    binding_id = connection.scalar(select(PlanRecommendation.id).limit(1))
    for table, row_id, column, value in (
        ("action_plan_runs", run_id, "mode", "live"),
        ("plan_recommendations", binding_id, "recommendation_version", "0" * 64),
        ("action_plan_reviews", review_id, "reason", "changed"),
    ):
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(f"UPDATE {table} SET {column} = :value WHERE id = :id"),
                {"value": value, "id": row_id},
            )
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": row_id})
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(
            ActionPlanReview.__table__.insert().values(
                id=uuid4(),
                plan_run_id=run_id,
                programme_revision_id=revision_id,
                plan_fingerprint="0" * 64,
                actor="authenticated_analysis_operator",
                decision="approved",
                reason="Wrong fingerprint must fail the composite foreign key.",
                reviewed_at=fixture.now,
                is_synthetic=True,
            )
        )
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(
            PlanRecommendation.__table__.insert().values(
                id=uuid4(),
                plan_run_id=run_id,
                career_run_id=fixture.parent.id,
                programme_revision_id=revision_id,
                recommendation_id=fixture.by_skill["model"].id,
                recommendation_version="0" * 64,
                is_synthetic=True,
            )
        )
    connection.commit()
    with pytest.raises(RuntimeError, match="Phase 6|Phase6|plan|Plan"):
        command.downgrade(config, "0006_career_alignment")
    connection.rollback()
    assert connection.scalar(text("SELECT count(*) FROM action_plan_runs")) == 1
    assert connection.scalar(text("SELECT count(*) FROM action_plan_reviews")) == 1
