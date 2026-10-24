"""Protected Phase 5 lifecycle checks using fictional, offline evidence only."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from career_helpers import TOKEN, career_settings, seed_career
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.main import create_app
from shiftos.models import CareerRecommendation, CareerReview, CareerRun, Job, ProgrammeRevision
from shiftos.repositories.career import enqueue_career, lock_career_for_job
from shiftos.services.ingestion.worker import fail_stale_jobs, run_once


@pytest.fixture
def career_context(session, database, tmp_path):
    records = seed_career(session)
    policy = tmp_path / "synthetic-permissions.json"
    policy.write_text(
        json.dumps({"version": "synthetic-career-api-1", "sources": {}}), encoding="utf-8"
    )
    settings = career_settings(analysis_permissions_path=policy)
    with TestClient(create_app(settings=settings, database=database)) as client:
        client.headers["X-Analysis-Token"] = TOKEN
        yield records, settings, client


def _submit(context, **updates):
    records, _, client = context
    body = records.request.model_dump(mode="json")
    body.update(updates)
    return client.post(f"/api/v1/programmes/{records.programme.id}/career-analyses", json=body)


def _complete(database, session, context):
    response = _submit(context)
    assert response.status_code == 202, response.text
    run_id = UUID(response.json()["id"])
    run = session.get(CareerRun, run_id)
    assert run_once(database, context[1]) == run.job_id
    session.expire_all()
    run = session.get(CareerRun, run_id)
    job = session.get(Job, run.job_id)
    assert job.status in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}, job.error
    return run


def test_queue_authorisation_freezes_cutoff_and_hides_unvalidated_quotes(session, career_context):
    records, _, client = career_context
    headers = client.headers.pop("X-Analysis-Token")
    assert _submit(career_context).status_code == 401
    client.headers["X-Analysis-Token"] = headers
    response = _submit(career_context, as_of=None)
    assert response.status_code == 202
    result = response.json()
    run = session.get(CareerRun, UUID(result["id"]))
    assert result["status"] == "QUEUED"
    assert result["request_json"]["source_text_withheld"] is True
    assert records.request.assertions[0].quote not in response.text
    assert run.mode == "offline" and len(run.manifest_json["inventory"]) == 4
    assert datetime.fromisoformat(run.request_json["as_of"]).utcoffset() is not None
    assert run.result_json == {} and session.get(Job, run.job_id).kind == "CAREER_ANALYSIS"


def test_idempotency_does_not_rebind_current_revision(session, career_context):
    records, _, client = career_context
    first = _submit(career_context, idempotency_key="synthetic-career-repeat")
    assert first.status_code == 202
    later = ProgrammeRevision(
        programme_id=records.programme.id, version_label="synthetic-later", is_synthetic=True
    )
    session.add(later)
    session.flush()
    records.programme.active_revision_id = later.id
    session.commit()
    replay = _submit(career_context, idempotency_key="synthetic-career-repeat")
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["programme_revision_id"] == str(records.revision.id)
    changed = _submit(career_context, idempotency_key="synthetic-career-repeat", mode="live")
    assert changed.status_code == 409
    assert session.scalar(select(func.count()).select_from(CareerRun)) == 1
    assert (
        client.get(f"/api/v1/programmes/{records.programme.id}/career-analyses").json()["total"]
        == 1
    )


def test_foreign_or_inconsistent_inventory_is_refused(session, career_context):
    assert _submit(career_context, revision_id=str(uuid4())).status_code == 404
    records, _, _ = career_context
    course = next(iter(records.courses.values()))
    course.is_synthetic = False
    session.commit()
    assert _submit(career_context).status_code == 409
    assert session.scalar(select(func.count()).select_from(CareerRun)) == 0


def test_real_offline_worker_persists_and_protected_sections_retrieve(
    database, session, career_context
):
    run = _complete(database, session, career_context)
    records, _, client = career_context
    response = client.get(f"/api/v1/career-analyses/{run.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["needs_evidence_revalidation"] is False
    assert set(data["result_json"]["course_ids"]) == {
        str(row.id) for row in records.courses.values()
    }
    assert data["model_usage_json"]["request_count"] == 0
    for section in ("occupations", "competencies", "evidence", "recommendations"):
        page = client.get(f"/api/v1/career-analyses/{run.id}/{section}?limit=1")
        assert page.status_code == 200, page.text
        assert page.json()["total"] > 0 and len(page.json()["items"]) == 1
        assert (
            client.get(f"/api/v1/career-analyses/{run.id}/{section}?limit=101").status_code == 422
        )
    client.headers.pop("X-Analysis-Token")
    assert client.get(f"/api/v1/career-analyses/{run.id}").status_code == 401
    assert client.get(f"/api/v1/career-analyses/{run.id}/evidence").status_code == 401


def test_worker_refuses_changed_frozen_inventory(database, session, career_context):
    queued = _submit(career_context)
    run = session.get(CareerRun, UUID(queued.json()["id"]))
    course = next(iter(career_context[0].courses.values()))
    course.course_name = "Changed synthetic title after submission"
    session.commit()
    assert run_once(database, career_context[1]) == run.job_id
    session.expire_all()
    assert session.get(Job, run.job_id).status == JobStatus.FAILED
    assert session.get(CareerRun, run.id).result_json == {}
    assert session.scalar(select(func.count()).select_from(CareerRecommendation)) == 0


def test_stale_recovery_includes_career_and_fences_late_writer(database, session, career_context):
    from shiftos.repositories.career import persist_result
    from shiftos.services.career.engine import evaluate

    run = enqueue_career(session, career_context[0].programme.id, career_context[0].request)
    job = session.get(Job, run.job_id)
    job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC) - timedelta(hours=2)
    session.commit()
    assert fail_stale_jobs(database) == 1
    session.expire_all()
    with pytest.raises(DomainError, match="not running"):
        lock_career_for_job(session, job.id)
    assert session.get(Job, job.id).status == JobStatus.FAILED
    assert session.get(CareerRun, run.id).result_json == {}
    records, settings, _ = career_context
    result = evaluate(
        session, records.programme.id, records.revision.id, records.request, settings, records.now
    )
    with pytest.raises(DomainError, match="not running"):
        persist_result(session, run, result)


def test_late_model_writer_cannot_publish_after_operator_recovery(
    database, session, career_context, monkeypatch
):
    from shiftos.services.career import reasoning

    response = _submit(career_context, mode="live")
    run = session.get(CareerRun, UUID(response.json()["id"]))
    attempts = []

    def recovered_while_reasoning(result, _settings):
        attempts.append(1)
        with database.session_factory() as independent:
            job = independent.get(Job, run.job_id)
            job.status, job.error = JobStatus.FAILED, "Synthetic explicit operator recovery"
            independent.commit()
        return result

    monkeypatch.setattr(reasoning, "explain", recovered_while_reasoning)
    assert run_once(database, career_context[1]) == run.job_id
    session.expire_all()
    assert attempts == [1]
    assert session.get(Job, run.job_id).error == "Synthetic explicit operator recovery"
    assert session.get(CareerRun, run.id).result_json == {}
    assert session.scalar(select(func.count()).select_from(CareerRecommendation)) == 0


def test_result_rows_and_job_completion_are_one_transaction(
    database, session, career_context, monkeypatch
):
    from shiftos.services.career import orchestrator

    original = orchestrator.persist_result

    def fail_after_result_flush(*args):
        original(*args)
        raise DomainError("CONFLICT", "Synthetic failure before completion commit", 409)

    monkeypatch.setattr(orchestrator, "persist_result", fail_after_result_flush)
    queued = _submit(career_context)
    run = session.get(CareerRun, UUID(queued.json()["id"]))
    assert run_once(database, career_context[1]) == run.job_id
    with database.session_factory() as independent:
        assert independent.get(Job, run.job_id).status == JobStatus.FAILED
        assert independent.get(CareerRun, run.id).result_json == {}
        assert independent.scalar(select(func.count()).select_from(CareerRecommendation)) == 0


def test_pending_sections_expose_job_state_and_restricted_sources_are_excluded(
    database, session, career_context
):
    records, _, client = career_context
    metadata = dict(records.version.metadata_json)
    permissions = dict(metadata["analysis_permissions"])
    permissions["excerpt_output_allowed"] = False
    metadata["analysis_permissions"] = permissions
    records.version.metadata_json = metadata
    session.commit()
    queued = _submit(career_context)
    run = session.get(CareerRun, UUID(queued.json()["id"]))
    for section in ("occupations", "competencies", "evidence", "recommendations"):
        response = client.get(f"/api/v1/career-analyses/{run.id}/{section}")
        assert response.status_code == 200
        assert response.json()["status"] == "QUEUED"
        assert response.json()["needs_evidence_revalidation"] is True
    assert run_once(database, career_context[1]) == run.job_id
    session.expire_all()
    persisted = session.get(CareerRun, run.id)
    assert persisted.result_json["status"] == "insufficient_evidence"
    assert persisted.result_json["evidence"] == []
    response = client.get(f"/api/v1/career-analyses/{run.id}")
    assert response.json()["result_json"]["status"] == "insufficient_evidence"
    assert records.request.assertions[0].quote not in response.text


def test_reviews_are_versioned_server_attributed_and_append_only(database, session, career_context):
    run = _complete(database, session, career_context)
    client = career_context[2]
    recommendation = session.scalar(
        select(CareerRecommendation).where(CareerRecommendation.run_id == run.id)
    )
    path = f"/api/v1/career-recommendations/{recommendation.id}/reviews"
    body = {
        "decision": "under_review",
        "reason": "Synthetic academic committee investigation",
        "expected_recommendation_version": recommendation.version_sha256,
    }
    assert client.post(path, json={**body, "actor": "spoofed_user"}).status_code == 422
    assert (
        client.post(path, json={**body, "expected_recommendation_version": "0" * 64}).status_code
        == 409
    )
    first = client.post(path, json=body)
    assert first.status_code == 201, first.text
    assert first.json()["actor"] == "authenticated_analysis_operator"
    second = client.post(path, json={**body, "decision": "needs_evidence"})
    assert second.status_code == 201
    history = client.get(path).json()
    assert history["total"] == 2
    assert [item["decision"] for item in history["items"]] == ["under_review", "needs_evidence"]
    row = session.get(CareerReview, UUID(first.json()["id"]))
    row.reason = "Cannot rewrite historical reason"
    with pytest.raises(ValueError, match="append-only"):
        session.flush()
    session.rollback()
    career_context[1].analysis_permissions_path.write_text(
        json.dumps({"version": "synthetic-review-withdrawn", "sources": {}}), encoding="utf-8"
    )
    withdrawn_history = client.get(path)
    assert withdrawn_history.status_code == 200
    assert all(
        item["needs_evidence_revalidation"] is True and item["evidence_access_limitations"]
        for item in withdrawn_history.json()["items"]
    )
    assert body["reason"] not in withdrawn_history.text
    recommendation.result_json = {"tampered": True}
    with pytest.raises(ValueError, match="append-only"):
        session.flush()
    session.rollback()


def test_policy_change_redacts_without_rewriting_and_blocks_approval(
    database, session, career_context
):
    run = _complete(database, session, career_context)
    _, settings, client = career_context
    historical = dict(run.result_json)
    recommendation = session.scalar(
        select(CareerRecommendation).where(CareerRecommendation.run_id == run.id)
    )
    settings.analysis_permissions_path.write_text(
        json.dumps({"version": "synthetic-withdrawn", "sources": {}}), encoding="utf-8"
    )
    response = client.get(f"/api/v1/career-analyses/{run.id}")
    assert response.json()["needs_evidence_revalidation"] is True
    assert response.json()["result_json"]["source_text_withheld"] is True
    assert "Synthetic Data" not in response.text
    body = {
        "decision": "approved",
        "reason": "Cannot approve a stale result",
        "expected_recommendation_version": recommendation.version_sha256,
    }
    assert (
        client.post(
            f"/api/v1/career-recommendations/{recommendation.id}/reviews", json=body
        ).status_code
        == 409
    )
    session.expire_all()
    assert session.get(CareerRun, run.id).result_json == historical
    assert session.scalar(select(func.count()).select_from(CareerReview)) == 0


def test_mocked_model_choices_do_not_leak_through_usage_after_source_withdrawal(
    database, session, career_context, monkeypatch
):
    from shiftos.api.routers.career import career_response
    from shiftos.services.career import reasoning

    records, settings, client = career_context
    selected = {}

    def comparison(result, _settings):
        citation = result.recommendations[0].citations[0]
        selected["quote"] = citation.quote
        result.model = {
            "status": "validated_option_comparison",
            "provider": "replit_claude",
            "actual_model": "claude-opus-5",
            "request_count": 1,
            "usage": {"input_tokens": 123, "output_tokens": 45},
            "observed_cost": None,
            "choices": [
                {
                    "recommendation_key": result.recommendations[0].key,
                    "citations": [citation.model_dump(mode="json")],
                }
            ],
        }
        return result

    monkeypatch.setattr(reasoning, "explain", comparison)
    queued = _submit(career_context, mode="live")
    run = session.get(CareerRun, UUID(queued.json()["id"]))
    assert run_once(database, settings) == run.job_id
    session.expire_all()
    stored = session.get(CareerRun, run.id)
    assert stored.result_json["model"]["choices"][0]["citations"][0]["quote"] == selected["quote"]
    assert "choices" not in stored.model_usage_json
    assert stored.model_usage_json["usage"] == {"input_tokens": 123, "output_tokens": 45}
    settings.analysis_permissions_path.write_text(
        json.dumps({"version": "synthetic-withdrawn-choices", "sources": {}}), encoding="utf-8"
    )
    for path in (
        f"/api/v1/career-analyses/{run.id}",
        f"/api/v1/programmes/{records.programme.id}/career-analyses",
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert selected["quote"] not in response.text
        items = response.json().get("items", [response.json()])
        assert all(item["model_usage_json"]["source_text_withheld"] is True for item in items)
    session.expire_all()
    historical = session.get(CareerRun, run.id)
    assert historical.result_json["model"]["choices"]
    # Exercise a historical response shape containing choices without modifying
    # the immutable committed row or bypassing the database history safeguards.
    legacy = SimpleNamespace(
        **{column.name: getattr(historical, column.name) for column in CareerRun.__table__.columns}
    )
    legacy.model_usage_json = {"choices": historical.result_json["model"]["choices"]}
    legacy_response = career_response(session, legacy, settings)
    assert selected["quote"] not in json.dumps(legacy_response, default=str)
    assert legacy_response["model_usage_json"]["source_text_withheld"] is True


@pytest.mark.parametrize("change", ["reference", "source", "record", "anchor", "active_revision"])
def test_changed_evidence_requires_revalidation(database, session, career_context, change):
    run = _complete(database, session, career_context)
    records, _, client = career_context
    if change == "reference":
        next(iter(records.references.values())).review_status = "rejected"
    elif change == "source":
        records.taxonomy_source.content_hash = "f" * 64
    elif change == "record":
        next(iter(records.skills.values())).description = "Changed synthetic competency fact"
    elif change == "anchor":
        next(iter(records.anchors.values())).excerpt = "Changed synthetic curriculum content"
    else:
        newer = ProgrammeRevision(
            programme_id=records.programme.id, version_label="synthetic-newer", is_synthetic=True
        )
        session.add(newer)
        session.flush()
        records.programme.active_revision_id = newer.id
    session.commit()
    response = client.get(f"/api/v1/career-analyses/{run.id}")
    assert response.json()["needs_evidence_revalidation"] is True
    assert response.json()["result_json"]["source_text_withheld"] is True


def test_terminal_results_cannot_be_edited_or_deleted(database, session, career_context):
    run = _complete(database, session, career_context)
    run.result_json = {"tampered": True}
    with pytest.raises(ValueError, match="immutable"):
        session.flush()
    session.rollback()
    run = session.get(CareerRun, run.id)
    session.delete(run)
    with pytest.raises(ValueError, match="immutable"):
        session.flush()
    session.rollback()


def test_review_foreign_snapshot_fails_composite_foreign_key(database, session, career_context):
    run = _complete(database, session, career_context)
    recommendation = session.scalar(
        select(CareerRecommendation).where(CareerRecommendation.run_id == run.id)
    )
    row = CareerReview(
        recommendation_id=recommendation.id,
        run_id=uuid4(),
        programme_revision_id=run.programme_revision_id,
        recommendation_version=recommendation.version_sha256,
        actor="authenticated_analysis_operator",
        decision="under_review",
        reason="Synthetic wrong ownership",
        reviewed_at=datetime.now(UTC),
        is_synthetic=True,
    )
    session.add(row)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
