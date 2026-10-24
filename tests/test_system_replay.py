"""Read-only change replay against real offline jobs and persisted source inputs."""

from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pathways_helpers import seed_pathways
from pydantic import ValidationError
from sqlalchemy import func, select

from shiftos.api.routers.replay import router
from shiftos.core.enums import EvidenceClass
from shiftos.core.errors import DomainError
from shiftos.main import create_app
from shiftos.models import (
    ActionPlanRun,
    Job,
    ProgrammeRevision,
    Source,
)
from shiftos.repositories.career import append_review
from shiftos.schemas.career import ReviewRequest
from shiftos.schemas.replay import ReplayRequest
from shiftos.services.ingestion.worker import run_once
from shiftos.services.replay import assess_replay


@pytest.fixture
def completed_plan(session, database, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Replay verification must not make provider/search requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    fixture = seed_pathways(session, database)
    app = create_app(settings=fixture.settings, database=database)
    if not any(path.endswith("/replay-assessment") for path in app.openapi()["paths"]):
        app.include_router(router)
    headers = {"X-Analysis-Token": fixture.settings.analysis_write_token.get_secret_value()}
    with TestClient(app, headers=headers) as client:
        response = client.post(
            f"/api/v1/career-analyses/{fixture.parent.id}/action-plans",
            json=fixture.request.model_dump(mode="json"),
        )
        assert response.status_code == 202, response.text
        assert run_once(database, fixture.settings)
        session.expire_all()
        fixture.plan = session.get(ActionPlanRun, UUID(response.json()["id"]))
        assert fixture.plan.result_json
        fixture.client = client
        yield fixture


def request(fixture, changes=None):
    return ReplayRequest(plan_run_id=fixture.plan.id, changes=changes or [])


def test_current_parent_chain_and_replay_assessment_are_read_only(session, completed_plan):
    fixture = completed_plan
    before = session.scalar(select(func.count()).select_from(Job))
    fingerprint = fixture.plan.fingerprint
    result = assess_replay(session, fixture.parent.programme_id, request(fixture), fixture.settings)
    assert all(row.current_eligible for row in result.eligibility)
    assert not result.actions and not result.impacts
    assert result.jobs_created == 0 and result.approvals_transferred is False
    assert session.scalar(select(func.count()).select_from(Job)) == before
    assert fixture.plan.fingerprint == fingerprint
    assert "excerpt" not in result.model_dump_json()


def test_exact_existing_assumption_is_no_effect_and_change_needs_new_plan(session, completed_plan):
    fixture = completed_plan
    assumption = fixture.plan.result_json["inputs"]["scenarios"][0]
    if not assumption:
        pytest.fail("Fixture must contain an explicit scenario assumption")
    same = request(fixture, [{"kind": "assumption", "assumption": assumption}])
    result = assess_replay(session, fixture.parent.programme_id, same, fixture.settings)
    assert result.impacts[0].classification == "no_effect"
    changed = same.model_copy(deep=True)
    changed.changes[0].assumption.rationale += " Additional fictional review condition."
    result = assess_replay(session, fixture.parent.programme_id, changed, fixture.settings)
    assert result.impacts[0].classification == "entire_plan_affected"
    assert [row.phase for row in result.actions] == ["phase6"]


def test_source_withdrawal_invalidates_eligibility_without_leaking_quotes(session, completed_plan):
    fixture = completed_plan
    source = fixture.records.version
    source.metadata_json = {**source.metadata_json, "rights_withdrawn": True}
    session.commit()
    result = assess_replay(
        session,
        fixture.parent.programme_id,
        request(fixture, [{"kind": "dataset_version", "id": source.id}]),
        fixture.settings,
    )
    assert all(not row.current_eligible for row in result.eligibility)
    assert result.impacts[0].eligibility_invalidated
    assert {row.phase for row in result.actions} >= {"phase5", "phase6"}
    assert "Synthetic reviewed assessment" not in result.model_dump_json()
    assert fixture.plan.result_json  # Historical snapshot remains immutable.


def test_nonfrozen_new_source_needs_applicability_review_never_no_effect(session, completed_plan):
    fixture = completed_plan
    source = Source(
        title="Fictional newly admitted source",
        publisher="Synthetic Fixture Generator",
        url="https://example.invalid/new-source",
        evidence_class=EvidenceClass.SYNTHETIC_DEMO,
        is_synthetic=True,
    )
    session.add(source)
    session.commit()
    result = assess_replay(
        session,
        fixture.parent.programme_id,
        request(fixture, [{"kind": "source", "id": source.id}]),
        fixture.settings,
    )
    assert result.impacts[0].classification == "needs_applicability_review"
    assert {row.phase for row in result.actions} == {"phase4", "phase5", "phase6"}


def test_new_revision_replays_lineage_and_does_not_transfer_approval(session, completed_plan):
    fixture = completed_plan
    revision = ProgrammeRevision(
        programme_id=fixture.parent.programme_id,
        version_label="Fictional revised inventory",
        is_synthetic=True,
    )
    session.add(revision)
    session.commit()
    result = assess_replay(
        session,
        fixture.parent.programme_id,
        request(fixture, [{"kind": "programme_revision", "id": revision.id}]),
        fixture.settings,
    )
    assert result.impacts[0].classification == "entire_plan_affected"
    assert {row.phase for row in result.actions} == {"phase4", "phase5", "phase6"}
    assert all(row.approvals_transfer is False for row in result.actions)


def test_parent_review_rejection_reports_targeted_pathway_and_stales_plan(session, completed_plan):
    fixture = completed_plan
    recommendation = fixture.by_skill["model"]
    latest = append_review(
        session,
        recommendation.id,
        ReviewRequest(
            decision="rejected",
            reason="Fictional human review rejection for replay test.",
            expected_recommendation_version=recommendation.version_sha256,
        ),
        fixture.settings,
    )
    result = assess_replay(
        session,
        fixture.parent.programme_id,
        request(fixture, [{"kind": "career_review", "id": latest.id}]),
        fixture.settings,
    )
    assert (
        next(row for row in result.eligibility if row.phase == "phase6").current_eligible is False
    )
    assert result.impacts[0].classification == "pathway_affected"
    assert len(result.impacts[0].affected_pathway_keys) == 1
    assert [row.phase for row in result.actions] == ["phase6"]


def test_crossprogramme_snapshot_is_not_found_and_wrong_parent_is_rejected(session, completed_plan):
    fixture = completed_plan
    with pytest.raises(DomainError) as error:
        assess_replay(session, uuid4(), request(fixture), fixture.settings)
    assert error.value.status_code == 404


def test_replay_api_requires_authorisation_and_returns_no_source_prose(completed_plan):
    fixture = completed_plan
    path = f"/api/v1/programmes/{fixture.parent.programme_id}/replay-assessment"
    response = fixture.client.post(path, json=request(fixture).model_dump(mode="json"))
    assert response.status_code == 200, response.text
    assert response.json()["jobs_created"] == 0
    response = fixture.client.post(
        path, json=request(fixture).model_dump(mode="json"), headers={"X-Analysis-Token": "wrong"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"plan_run_id": str(uuid4()), "changes": [{"kind": "source"}]},
        {"plan_run_id": str(uuid4()), "changes": [{"kind": "assumption", "id": str(uuid4())}]},
        {
            "plan_run_id": str(uuid4()),
            "changes": [{"kind": "source", "id": str(uuid4()), "url": "https://example.invalid"}],
        },
    ],
)
def test_replay_inputs_are_typed_bounded_and_do_not_accept_arbitrary_urls(payload):
    with pytest.raises(ValidationError):
        ReplayRequest.model_validate(payload)
