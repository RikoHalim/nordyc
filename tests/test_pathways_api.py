"""Offline protected action-plan lifecycle, provenance and failure atomicity."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from career_helpers import TOKEN
from fastapi.testclient import TestClient
from pathways_helpers import seed_pathways
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.main import create_app
from shiftos.models import (
    ActionPlanReview,
    ActionPlanRun,
    EvidenceReference,
    Job,
    PlanRecommendation,
    SDGReference,
)
from shiftos.repositories.career import append_review as append_career_review
from shiftos.repositories.pathways import lock_plan_for_job
from shiftos.schemas.career import ReviewRequest
from shiftos.services.ingestion.worker import fail_stale_jobs, run_once


@pytest.fixture
def plan_context(session, database, tmp_path):
    fixture = seed_pathways(session, database, tmp_path)
    policy = tmp_path / "plan-permissions.json"
    policy.write_text(
        fixture.settings.analysis_permissions_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    fixture.settings = fixture.settings.model_copy(update={"analysis_permissions_path": policy})
    with TestClient(create_app(settings=fixture.settings, database=database)) as client:
        client.headers["X-Analysis-Token"] = TOKEN
        yield fixture, client


def _submit(context, **updates):
    fixture, client = context
    body = fixture.request.model_dump(mode="json")
    body.update(updates)
    return client.post(f"/api/v1/career-analyses/{fixture.parent_run.id}/action-plans", json=body)


def _complete(database, session, context):
    response = _submit(context)
    assert response.status_code == 202, response.text
    run = session.get(ActionPlanRun, UUID(response.json()["id"]))
    assert run_once(database, context[0].settings) == run.job_id
    session.expire_all()
    run = session.get(ActionPlanRun, run.id)
    job = session.get(Job, run.job_id)
    assert job.status in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}, job.error
    return run


def test_queue_auth_freezes_parent_bindings_and_hides_pending_source_text(session, plan_context):
    fixture, client = plan_context
    client.headers.pop("X-Analysis-Token")
    assert _submit(plan_context).status_code == 401
    client.headers["X-Analysis-Token"] = TOKEN
    response = _submit(plan_context)
    assert response.status_code == 202, response.text
    run = session.get(ActionPlanRun, UUID(response.json()["id"]))
    assert run.career_fingerprint == fixture.parent_run.fingerprint
    assert run.request_json["as_of"]
    assert response.json()["request_json"]["source_text_withheld"] is True
    assert fixture.records.request.assertions[0].quote not in response.text
    bindings = session.scalars(
        select(PlanRecommendation).where(PlanRecommendation.plan_run_id == run.id)
    ).all()
    assert {row.recommendation_id for row in bindings} == {
        row.id for row in fixture.recommendations
    }
    assert all(
        row.career_run_id == fixture.parent_run.id
        and row.programme_revision_id == run.programme_revision_id
        for row in bindings
    )
    assert session.get(Job, run.job_id).kind == "ACTION_PLAN"
    for section in ("pathways", "resources", "scenarios", "sdg", "evidence"):
        page = client.get(f"/api/v1/action-plans/{run.id}/{section}").json()
        assert page["status"] == "QUEUED" and page["needs_evidence_revalidation"] is True


def test_idempotent_plan_replay_and_changed_request_conflict(session, plan_context):
    first = _submit(plan_context, idempotency_key="synthetic-plan-replay")
    assert first.status_code == 202
    replay = _submit(plan_context, idempotency_key="synthetic-plan-replay")
    assert replay.json()["id"] == first.json()["id"]
    assert (
        _submit(plan_context, idempotency_key="synthetic-plan-replay", mode="live").status_code
        == 409
    )
    assert session.scalar(select(func.count()).select_from(ActionPlanRun)) == 1
    fixture, client = plan_context
    history = client.get(f"/api/v1/career-analyses/{fixture.parent_run.id}/action-plans")
    assert history.status_code == 200 and history.json()["total"] == 1


def test_wrong_parent_recommendation_and_duplicate_selection_are_refused(plan_context):
    assert _submit(plan_context, recommendation_ids=[str(uuid4())]).status_code == 409
    value = str(plan_context[0].recommendations[0].id)
    assert _submit(plan_context, recommendation_ids=[value, value]).status_code == 422
    assert _submit(plan_context, phase4_analysis_id=str(uuid4())).status_code == 409
    assert _submit(plan_context, previous_plan_id=str(uuid4())).status_code == 409
    client = plan_context[1]
    assert (
        client.post(f"/api/v1/career-analyses/{uuid4()}/action-plans", json={}).status_code == 404
    )


def test_actual_worker_persists_mixed_original_and_synthetic_evidence_and_typed_sections(
    database, session, plan_context
):
    run = _complete(database, session, plan_context)
    fixture, client = plan_context
    response = client.get(f"/api/v1/action-plans/{run.id}")
    assert response.status_code == 200, response.text
    output = response.json()
    assert output["needs_evidence_revalidation"] is False
    result = output["result_json"]
    assert set(result["overview"]["course_ids"]) == {
        str(row.id) for row in fixture.records.courses.values()
    }
    assert result["career_fingerprint"] == fixture.parent_run.fingerprint
    assert len(result["scenarios"]) == 2 and result["pathways"]
    assert {item["is_synthetic"] for item in result["evidence"]} == {True, False}
    assert result["model"]["request_count"] == 0
    assert result["review"].get("automatic_curriculum_change", False) is False
    for section in ("pathways", "resources", "scenarios", "sdg", "evidence"):
        page = client.get(f"/api/v1/action-plans/{run.id}/{section}?limit=1")
        assert page.status_code == 200, page.text
        assert page.json()["total"] > 0 and len(page.json()["items"]) == 1
        assert client.get(f"/api/v1/action-plans/{run.id}/{section}?limit=101").status_code == 422
    first = result["pathways"][0]
    steps = client.get(f"/api/v1/action-plans/{run.id}/pathways/{first['key']}/steps")
    assert steps.status_code == 200 and steps.json()["total"] == len(first["steps"])
    assert client.get(f"/api/v1/action-plans/{run.id}/pathways/missing/steps").status_code == 404
    comparison = client.get(f"/api/v1/action-plans/{run.id}/comparison")
    assert (
        comparison.status_code == 200 and len(comparison.json()["comparison"]["scenario_keys"]) == 2
    )
    with database.session_factory() as independent:
        assert independent.get(ActionPlanRun, run.id).fingerprint == run.fingerprint
        assert independent.get(Job, run.job_id).status in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}


def test_new_parent_review_fences_pending_worker(database, session, plan_context):
    fixture, _ = plan_context
    response = _submit(plan_context)
    run = session.get(ActionPlanRun, UUID(response.json()["id"]))
    recommendation = fixture.by_skill["model"]
    append_career_review(
        session,
        recommendation.id,
        ReviewRequest(
            decision="rejected",
            reason="Synthetic new committee rejection",
            expected_recommendation_version=recommendation.version_sha256,
        ),
        fixture.settings,
    )
    assert run_once(database, fixture.settings) == run.job_id
    session.expire_all()
    assert session.get(Job, run.job_id).status == JobStatus.FAILED
    assert session.get(ActionPlanRun, run.id).result_json == {}


@pytest.mark.parametrize(
    "mutation",
    [
        "resource_reference",
        "resource_version",
        "official_sdg",
        "parent_goal_reference",
        "parent_review",
    ],
)
def test_changed_plan_dependency_redacts_output_and_blocks_current_approval(
    database, session, plan_context, mutation
):
    run = _complete(database, session, plan_context)
    fixture, client = plan_context
    preserved = dict(run.result_json)
    if mutation == "resource_reference":
        fixture.resources["model-workbook"].review_status = "rejected"
    elif mutation == "resource_version":
        fixture.resource_versions["model-workbook"].content_sha256 = "f" * 64
    elif mutation == "official_sdg":
        session.get(
            SDGReference, fixture.sdg_targets["4.4"].id
        ).description = "Changed target statement for source revalidation test"
    elif mutation == "parent_goal_reference":
        goal = session.get(SDGReference, fixture.sdg_targets["4"].id)
        target = session.get(SDGReference, fixture.sdg_targets["4.4"].id)
        reference = session.get(EvidenceReference, goal.evidence_id)
        assert reference.id != target.evidence_id
        reference.review_status = "rejected"
        assert session.get(EvidenceReference, target.evidence_id).review_status == "reviewed"
    else:
        row = fixture.by_skill["model"]
        append_career_review(
            session,
            row.id,
            ReviewRequest(
                decision="rejected",
                reason="Synthetic later recommendation rejection",
                expected_recommendation_version=row.version_sha256,
            ),
            fixture.settings,
        )
    session.commit()
    response = client.get(f"/api/v1/action-plans/{run.id}")
    assert response.status_code == 200
    assert response.json()["needs_evidence_revalidation"] is True
    assert response.json()["result_json"]["source_text_withheld"] is True
    assert client.get(f"/api/v1/action-plans/{run.id}/evidence").json()["items"] == []
    body = {
        "decision": "approved",
        "reason": "Cannot approve stale test plan",
        "expected_plan_fingerprint": run.fingerprint,
    }
    assert client.post(f"/api/v1/action-plans/{run.id}/reviews", json=body).status_code == 409
    session.expire_all()
    assert session.get(ActionPlanRun, run.id).result_json == preserved


def test_plan_review_history_is_server_attributed_versioned_and_append_only(
    database, session, plan_context
):
    run = _complete(database, session, plan_context)
    fixture, client = plan_context
    path = f"/api/v1/action-plans/{run.id}/reviews"
    body = {
        "decision": "under_review",
        "reason": "Explicit synthetic operator review, not university implementation approval",
        "expected_plan_fingerprint": run.fingerprint,
    }
    assert client.post(path, json={**body, "actor": "impersonated professor"}).status_code == 422
    assert (
        client.post(path, json={**body, "expected_plan_fingerprint": "0" * 64}).status_code == 409
    )
    first = client.post(path, json=body)
    assert first.status_code == 201, first.text
    assert first.json()["actor"] == "authenticated_analysis_operator"
    assert client.post(path, json={**body, "decision": "needs_evidence"}).status_code == 201
    assert client.get(path).json()["total"] == 2
    row = session.get(ActionPlanReview, UUID(first.json()["id"]))
    row.reason = "Tamper with audit history"
    with pytest.raises(ValueError, match="append-only"):
        session.flush()
    session.rollback()
    fixture.settings.analysis_permissions_path.write_text(
        json.dumps({"version": "withdrawn-plan", "sources": {}}), encoding="utf-8"
    )
    history = client.get(path)
    assert all(
        item["needs_evidence_revalidation"] and item["evidence_access_limitations"]
        for item in history.json()["items"]
    )
    assert body["reason"] not in history.text


def test_stale_action_plan_job_is_recoverable_and_late_results_are_fenced(
    database, session, plan_context
):
    response = _submit(plan_context)
    run = session.get(ActionPlanRun, UUID(response.json()["id"]))
    job = session.get(Job, run.job_id)
    job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC) - timedelta(hours=2)
    session.commit()
    assert fail_stale_jobs(database) == 1
    session.expire_all()
    with pytest.raises(DomainError, match="not running"):
        lock_plan_for_job(session, job.id, plan_context[0].settings)
    assert session.get(ActionPlanRun, run.id).result_json == {}


def test_plan_result_and_job_completion_commit_atomically(
    database, session, plan_context, monkeypatch
):
    from shiftos.services.pathways import orchestrator

    original = orchestrator.persist_result

    def fail_before_completion(*args):
        original(*args)
        raise DomainError("CONFLICT", "Synthetic completion failure", 409)

    monkeypatch.setattr(orchestrator, "persist_result", fail_before_completion)
    response = _submit(plan_context)
    run = session.get(ActionPlanRun, UUID(response.json()["id"]))
    assert run_once(database, plan_context[0].settings) == run.job_id
    with database.session_factory() as independent:
        assert independent.get(ActionPlanRun, run.id).result_json == {}
        assert independent.get(Job, run.job_id).status == JobStatus.FAILED


def test_recovered_worker_cannot_publish_after_model_comparison(
    database, session, plan_context, monkeypatch
):
    from shiftos.services.pathways import reasoning

    queued = _submit(plan_context, mode="live")
    run = session.get(ActionPlanRun, UUID(queued.json()["id"]))
    attempts = []

    def recover_during_comparison(result, _settings):
        attempts.append(1)
        with database.session_factory() as independent:
            job = independent.get(Job, run.job_id)
            job.status, job.error = JobStatus.FAILED, "Synthetic operator recovered this worker"
            independent.commit()
        return result

    monkeypatch.setattr(reasoning, "explain", recover_during_comparison)
    assert run_once(database, plan_context[0].settings) == run.job_id
    session.expire_all()
    assert attempts == [1]
    assert session.get(Job, run.job_id).error == "Synthetic operator recovered this worker"
    assert session.get(ActionPlanRun, run.id).result_json == {}


def test_mocked_model_citations_are_withheld_after_source_policy_withdrawal(
    database, session, plan_context, monkeypatch
):
    from shiftos.services.pathways import reasoning

    fixture, client = plan_context
    selected = {}

    def compare(result, _settings):
        evidence = result.evidence[0]
        selected["quote"] = evidence.excerpt
        result.model = {
            "status": "validated_pathway_review",
            "provider": "replit_claude",
            "actual_model": "claude-opus-5",
            "request_count": 1,
            "observed_cost": None,
            "usage": {"input_tokens": 123, "output_tokens": 45},
            "choices": [{"citations": [{"reference_id": evidence.id, "quote": evidence.excerpt}]}],
        }
        return result

    monkeypatch.setattr(reasoning, "explain", compare)
    queued = _submit(plan_context, mode="live")
    run = session.get(ActionPlanRun, UUID(queued.json()["id"]))
    assert run_once(database, fixture.settings) == run.job_id
    session.expire_all()
    historical = session.get(ActionPlanRun, run.id)
    assert historical.result_json["model"]["choices"]
    assert "choices" not in historical.model_usage_json
    assert historical.model_usage_json["usage"]["input_tokens"] == 123
    fixture.settings.analysis_permissions_path.write_text(
        json.dumps({"version": "withdrawn-model-plan", "sources": {}}), encoding="utf-8"
    )
    for path in (
        f"/api/v1/action-plans/{run.id}",
        f"/api/v1/career-analyses/{fixture.parent_run.id}/action-plans",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert selected["quote"] not in response.text
        items = response.json().get("items", [response.json()])
        assert all(item["model_usage_json"]["source_text_withheld"] is True for item in items)
    session.expire_all()
    assert session.get(ActionPlanRun, run.id).result_json["model"]["choices"]


def test_completed_plan_and_bindings_are_immutable(database, session, plan_context):
    run = _complete(database, session, plan_context)
    run.result_json = {"tampered": True}
    with pytest.raises(ValueError, match="immutable"):
        session.flush()
    session.rollback()
    binding = session.scalar(
        select(PlanRecommendation).where(PlanRecommendation.plan_run_id == run.id)
    )
    binding.recommendation_version = "f" * 64
    with pytest.raises(ValueError, match="append-only"):
        session.flush()
    session.rollback()


def test_wrong_plan_review_fingerprint_fails_composite_foreign_key(database, session, plan_context):
    run = _complete(database, session, plan_context)
    session.add(
        ActionPlanReview(
            plan_run_id=run.id,
            programme_revision_id=run.programme_revision_id,
            plan_fingerprint="0" * 64,
            actor="authenticated_analysis_operator",
            decision="under_review",
            reason="Synthetic invalid version",
            reviewed_at=datetime.now(UTC),
            is_synthetic=True,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
