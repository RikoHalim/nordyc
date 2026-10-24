"""Phase 6 evidence, ordering and proposal acceptance with no external requests."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from pathways_helpers import seed_parent, seed_pathways
from pydantic import ValidationError

from shiftos.core.errors import DomainError
from shiftos.models import Job
from shiftos.repositories.career import append_review
from shiftos.schemas.career import ReviewRequest
from shiftos.schemas.pathways import PlanRequest, PlanResult, PrerequisiteBinding


@pytest.fixture(autouse=True)
def no_external_request(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Academic pathway acceptance must not contact external providers")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def test_frozen_career_parent_retains_exact_recommendations_and_explicit_review_history(
    session, database
):
    from shiftos.services.pathways.engine import _load_parent

    fixture = seed_parent(session, database)
    parent, career, rows, latest, history = _load_parent(
        session, fixture.parent.id, fixture.settings, datetime.now(UTC)
    )
    assert parent.id == fixture.parent.id
    assert career.programme_revision_id == fixture.records.revision.id
    assert {row.id for row in rows} == {row.id for row in fixture.recommendations}
    assert len(latest) == len(history) == 5
    assert all(review.actor == "authenticated_analysis_operator" for review in history)
    assert all(
        review.recommendation_version
        == next(row.version_sha256 for row in rows if row.id == review.recommendation_id)
        for review in history
    )


@pytest.mark.parametrize(
    "mutation", ["missing_parent", "future_cutoff", "cutoff_before_parent", "source_withdrawn"]
)
def test_parent_source_revision_and_known_at_cutoff_guards_are_preserved(
    session, database, mutation
):
    from shiftos.services.pathways.engine import _load_parent

    fixture = seed_parent(session, database)
    parent_id, cutoff = fixture.parent.id, datetime.now(UTC)
    if mutation == "missing_parent":
        parent_id = uuid4()
    elif mutation == "future_cutoff":
        cutoff += timedelta(days=1)
    elif mutation == "cutoff_before_parent":
        cutoff = fixture.records.now - timedelta(days=1)
    else:
        fixture.records.version.metadata_json = {
            **fixture.records.version.metadata_json,
            "rights_withdrawn": True,
        }
        session.commit()
    with pytest.raises(DomainError):
        _load_parent(session, parent_id, fixture.settings, cutoff)


def test_incomplete_parent_job_cannot_be_used_as_a_planning_result(session, database):
    from shiftos.core.enums import JobStatus
    from shiftos.services.pathways.engine import _load_parent

    fixture = seed_parent(session, database)
    parent_job = session.get(Job, fixture.parent.job_id)
    parent_job.status = JobStatus.FAILED
    session.commit()
    with pytest.raises(DomainError, match="Complete the parent"):
        _load_parent(session, fixture.parent.id, fixture.settings, datetime.now(UTC))


def evaluate(session, fixture, request=None):
    from shiftos.services.pathways.engine import evaluate

    return evaluate(
        session, fixture.parent.id, request or fixture.request, fixture.settings, fixture.now
    )


def pathway_for(result, fixture, skill):
    return next(
        row for row in result.pathways if row.recommendation_id == fixture.by_skill[skill].id
    )


def test_synthetic_action_plan_preserves_eight_sections_and_exact_phase5_lineage(session, database):
    fixture = seed_pathways(session, database)
    result = evaluate(session, fixture)
    assert PlanResult.model_validate(result.model_dump(mode="json")) == result
    assert result.is_synthetic and result.career_run_id == fixture.parent.id
    assert result.career_fingerprint == fixture.parent.fingerprint
    assert result.programme_revision_id == fixture.records.revision.id
    assert result.overview.institution_id == fixture.records.institution.id
    assert set(result.overview.course_ids) == {row.id for row in fixture.records.courses.values()}
    assert result.career.competencies and result.career.occupations and result.recommendations
    assert result.pathways and result.scenarios and result.sdg_alignments and result.review
    snapshots = {row.id: row for row in result.recommendations}
    assert set(snapshots) == {row.id for row in fixture.recommendations}
    for source in fixture.recommendations:
        assert snapshots[source.id].version_sha256 == source.version_sha256
        assert snapshots[source.id].recommendation.model_dump(mode="json") == source.result_json
    assert result.model["request_count"] == 0
    assert result.model["observed_cost"] is None


def test_partial_and_explicit_gap_create_conditional_assessed_paths_unknown_is_review_only(
    session, database
):
    fixture = seed_pathways(session, database)
    result = evaluate(session, fixture)
    for skill in ("model", "security"):
        pathway = pathway_for(result, fixture, skill)
        assert pathway.pathway_type == "academic_intervention"
        assert pathway.recommendation_version == fixture.by_skill[skill].version_sha256
        assert pathway.skill_id == fixture.records.skills[skill].id
        assert len(pathway.steps) >= 3
        assert any(step.step_type == "proposed_practice" for step in pathway.steps)
        assert any(step.step_type == "assessment_design" for step in pathway.steps)
        assert pathway.no_change_option["category"] == "no_change" and pathway.alternatives
        assert pathway.review_status in {"proposed", "needs_evidence"}
        assert pathway.automatic_curriculum_change is False
    unknown = pathway_for(result, fixture, "governance")
    assert unknown.pathway_type == "evidence_review"
    assert not any(
        step.step_type in {"proposed_practice", "assessment_design"} for step in unknown.steps
    )
    assert all(step.achieved_competence is False for row in result.pathways for step in row.steps)


def test_no_change_recommendation_does_not_become_compulsory_reskilling(session, database):
    fixture = seed_pathways(session, database)
    result = evaluate(session, fixture)
    recommendation = next(
        row for row in result.recommendations if row.id == fixture.by_skill["sql"].id
    )
    assert recommendation.consideration_status == "no_change"
    assert not any(row.recommendation_id == recommendation.id for row in result.pathways)


def test_new_rejected_review_blocks_training_without_overwriting_older_decision(session, database):
    fixture = seed_pathways(session, database)
    recommendation = fixture.by_skill["security"]
    append_review(
        session,
        recommendation.id,
        ReviewRequest(
            decision="rejected",
            reason="Explicit fictional latest operator decision rejects consideration.",
            expected_recommendation_version=recommendation.version_sha256,
        ),
        fixture.settings,
    )
    fixture.now = datetime.now(UTC)
    result = evaluate(session, fixture)
    rejected = next(row for row in result.recommendations if row.id == recommendation.id)
    assert rejected.consideration_status == "rejected" and len(rejected.reviews) == 2
    assert not any(row.recommendation_id == recommendation.id for row in result.pathways)


def test_unreviewed_parent_recommendation_requires_evidence_before_substantive_activity(
    session, database
):
    fixture = seed_pathways(session, database, approve=False)
    with pytest.raises(DomainError, match="ineligible"):
        evaluate(session, fixture)
    request = fixture.request.model_copy(update={"durations": []})
    result = evaluate(session, fixture, request)
    assert all(
        row.consideration_status in {"needs_review", "no_change"} for row in result.recommendations
    )
    assert not any(
        step.step_type == "proposed_practice" for row in result.pathways for step in row.steps
    )


def test_exact_resource_duration_is_effort_with_unknown_remaining_steps_not_calendar_total(
    session, database
):
    fixture = seed_pathways(session, database)
    result = evaluate(session, fixture)
    model = pathway_for(result, fixture, "model")
    practice = next(step for step in model.steps if step.key == "practice")
    assert practice.duration.hours == 3 and practice.duration.basis_type == "source"
    assert practice.duration.component == "learning" and practice.duration.citations
    assert practice.duration.guaranteed_completion_time is False
    assert (
        model.known_hours >= 3 and model.total_hours is None and model.unknown_duration_steps >= 1
    )
    security = pathway_for(result, fixture, "security")
    assert security.total_hours is None
    assert all(resource.verification_status == "synthetic_demo" for resource in result.resources)
    assert all(
        resource.cost_status == "unknown" and resource.cost_amount is None
        for resource in result.resources
    )


def test_explicit_reviewer_duration_is_labelled_assumption_not_source_claim(session, database):
    fixture = seed_pathways(session, database)
    request = fixture.request.model_copy(deep=True)
    request.durations[0].basis_type = "planning_assumption"
    request.durations[0].reference_id = None
    request.durations[0].quote = None
    request.durations[0].hours = 2
    request.durations[
        0
    ].basis = "Explicit fictional reviewer effort assumption, not a provider promise."
    result = evaluate(session, fixture, request)
    practice = next(
        step for step in pathway_for(result, fixture, "model").steps if step.key == "practice"
    )
    assert practice.duration.hours == 2 and practice.duration.basis_type == "planning_assumption"
    assert not practice.duration.citations and not practice.duration.guaranteed_completion_time


@pytest.mark.parametrize(
    "mutation",
    ["withdrawn", "unreviewed", "wrong_skill", "contradictory_free_cost", "wrong_original_url"],
)
def test_resource_rights_identity_cost_and_original_review_fail_closed(session, database, mutation):
    fixture = seed_pathways(session, database)
    resource = fixture.resources["model-workbook"]
    metadata = dict(resource.metadata_json)
    original = dict(metadata["learning_resource"])
    request = fixture.request.model_copy(deep=True)
    request.durations = []
    if mutation == "withdrawn":
        metadata["rights_withdrawn"] = True
    elif mutation == "unreviewed":
        resource.review_status = "needs_review"
    elif mutation == "wrong_skill":
        original["related_skill_ids"] = [str(fixture.records.skills["governance"].id)]
    elif mutation == "contradictory_free_cost":
        original.update(
            cost_status="free",
            cost_amount="10",
            cost_currency="MYR",
            cost_verified_at=fixture.now.isoformat(),
        )
    else:
        original["url"] = "https://example.invalid/unregistered-other-original"
    metadata["learning_resource"] = original
    resource.metadata_json = metadata
    session.commit()
    try:
        result = evaluate(session, fixture, request)
    except DomainError:
        return
    assert not any(
        row.reference_id == f"learning_resource:{resource.id}" for row in result.resources
    )


@pytest.mark.parametrize(
    "mutation", ["wrong_quote", "wrong_hours", "unknown_reference", "wrong_component"]
)
def test_duration_cannot_be_fabricated_from_an_unrelated_or_inconsistent_source(
    session, database, mutation
):
    fixture = seed_pathways(session, database)
    request = fixture.request.model_copy(deep=True)
    binding = request.durations[0]
    if mutation == "wrong_quote":
        binding.quote = "Fabricated original-provider claim guarantees completion in one hour."
    elif mutation == "wrong_hours":
        binding.hours = 999
    elif mutation == "unknown_reference":
        binding.reference_id = "learning_resource:unregistered"
    else:
        binding.component = "assessment"
    try:
        result = evaluate(session, fixture, request)
    except DomainError:
        return
    practice = next(
        step for step in pathway_for(result, fixture, "model").steps if step.key == "practice"
    )
    assert practice.duration.hours is None and practice.duration.basis_type == "unknown"


@pytest.mark.parametrize(
    "entries",
    [
        [("a", 1, ["b"]), ("b", 2, ["a"])],
        [("a", 1, ["a"])],
        [("a", 1, ["missing"])],
        [("a", 1, []), ("a", 2, [])],
        [("a", 1, []), ("b", 1, [])],
        [("a", 2, []), ("b", 1, ["a"])],
    ],
)
def test_invalid_or_cyclic_pathway_dependencies_are_rejected(entries):
    from shiftos.services.pathways.engine import _validate_dependency_graph

    with pytest.raises(DomainError):
        _validate_dependency_graph(entries)


def test_partially_ordered_pathway_does_not_need_an_invented_dependency_chain():
    from shiftos.services.pathways.engine import _validate_dependency_graph

    _validate_dependency_graph(
        [("review", 1, []), ("resource_review", 2, []), ("decision", 3, ["review"])]
    )


def test_prerequisite_requires_explicit_source_to_skill_review_not_step_order(session, database):
    fixture = seed_pathways(session, database)
    without = evaluate(session, fixture)
    assert not pathway_for(without, fixture, "model").prerequisites
    request = fixture.request.model_copy(deep=True)
    resource = fixture.resources["model-workbook"]
    request.prerequisites = [
        PrerequisiteBinding(
            target_skill_id=fixture.records.skills["model"].id,
            prerequisite_skill_id=fixture.records.skills["sql"].id,
            reference_id=f"learning_resource:{resource.id}",
            quote=resource.excerpt,
            basis="Fictional original states SQL prerequisite; enrolment coverage remains unknown.",
            reviewed=True,
            reviewed_at=fixture.now,
        )
    ]
    result = evaluate(session, fixture, request)
    prerequisites = pathway_for(result, fixture, "model").prerequisites
    assert len(prerequisites) == 1
    assert prerequisites[0].skill_id == fixture.records.skills["sql"].id
    assert prerequisites[0].status == "source_supported" and prerequisites[0].citations


@pytest.mark.parametrize("mutation", ["wrong_skill", "wrong_quote", "unreviewed"])
def test_unsupported_prerequisites_stay_unverified(session, database, mutation):
    fixture = seed_pathways(session, database)
    resource = fixture.resources["model-workbook"]
    request = fixture.request.model_copy(deep=True)
    prerequisite = PrerequisiteBinding(
        target_skill_id=fixture.records.skills["model"].id,
        prerequisite_skill_id=fixture.records.skills["sql"].id,
        reference_id=f"learning_resource:{resource.id}",
        quote=resource.excerpt,
        basis="Fictional prerequisite review for this resource only.",
        reviewed=True,
        reviewed_at=fixture.now,
    )
    if mutation == "wrong_skill":
        prerequisite.prerequisite_skill_id = fixture.records.skills["governance"].id
    elif mutation == "wrong_quote":
        prerequisite.quote = "Unregistered source claims a new mandatory prerequisite."
    else:
        prerequisite.reviewed = False
    request.prerequisites = [prerequisite]
    try:
        result = evaluate(session, fixture, request)
    except DomainError:
        return
    assert all(
        row.status == "needs_review" for row in pathway_for(result, fixture, "model").prerequisites
    )


def test_two_scenarios_preserve_assumptions_separately_from_frozen_career_observations(
    session, database
):
    fixture = seed_pathways(session, database)
    before = deepcopy(fixture.parent.result_json)
    result = evaluate(session, fixture)
    assert len(result.scenarios) == 2
    assert {row.key for row in result.scenarios} == {
        "accelerated_ai_adoption",
        "gradual_workforce_transformation",
    }
    assert all(row.is_forecast is False and row.probability is None for row in result.scenarios)
    assert all(row.assumption.rationale and row.uncertainties for row in result.scenarios)
    assert result.scenarios[0].comparison_dimensions == result.scenarios[1].comparison_dimensions
    assert result.comparison.dimensions and result.comparison.explanation
    assert fixture.parent.result_json == before == result.career.model_dump(mode="json")
    assert set(
        result.comparison.changed_recommendation_ids
        + result.comparison.unchanged_recommendation_ids
    ) <= {row.id for row in result.recommendations}


def test_scoped_observed_task_changes_only_conditional_review_priority_under_explicit_assumption(
    session, database
):
    fixture = seed_pathways(session, database, observed_ai=True)
    before = deepcopy(fixture.parent.result_json)
    result = evaluate(session, fixture)
    assert fixture.by_skill["model"].id in result.comparison.changed_recommendation_ids
    accelerated = next(row for row in result.scenarios if row.key == "accelerated_ai_adoption")
    gradual = next(row for row in result.scenarios if row.key == "gradual_workforce_transformation")
    assert (
        next(
            row
            for row in accelerated.priorities
            if row.recommendation_id == fixture.by_skill["model"].id
        ).priority
        == "conditional_priority"
    )
    assert (
        next(
            row
            for row in gradual.priorities
            if row.recommendation_id == fixture.by_skill["model"].id
        ).priority
        == "review_first"
    )
    assert fixture.by_skill["sql"].id in result.comparison.unchanged_recommendation_ids
    assert result.career.model_dump(mode="json") == before
    assert accelerated.is_forecast is False and accelerated.probability is None
    # The scenario method must abstain if the admitted task is later classified as
    # historical context; an old observation does not become a new adoption forecast.
    from shiftos.services.pathways.scenarios import build_scenarios

    historical = deepcopy(result.evidence)
    for pointer in historical:
        if pointer.kind == "ai_evidence":
            pointer.historical_context_only = True
    stale_scenarios, stale_comparison = build_scenarios(
        result.career, result.recommendations, historical, result.inputs.scenarios
    )
    assert not any(
        priority.priority == "conditional_priority"
        for scenario in stale_scenarios
        for priority in scenario.priorities
    )
    assert not stale_comparison.changed_recommendation_ids


@pytest.mark.parametrize(
    "mutation",
    [
        "recommendation_version",
        "skill_identity",
        "attendance_mastery",
        "fabricated_activity",
        "invented_duration",
        "forecast",
        "measured_sdg_impact",
        "invented_approval",
        "fabricated_citation",
    ],
)
def test_frozen_plan_validation_rejects_substantive_fabrication_and_lineage_changes(
    session, database, mutation
):
    from shiftos.services.pathways.engine import validate_plan_result

    fixture = seed_pathways(session, database)
    result = evaluate(session, fixture).model_dump(mode="json")
    pathway = next(
        row
        for row in result["pathways"]
        if row["recommendation_id"] == str(fixture.by_skill["model"].id)
    )
    if mutation == "recommendation_version":
        pathway["recommendation_version"] = "0" * 64
    elif mutation == "skill_identity":
        pathway["skill_id"] = str(uuid4())
    elif mutation == "attendance_mastery":
        pathway["steps"][0]["achieved_competence"] = True
    elif mutation == "fabricated_activity":
        pathway["steps"][0]["activity"] = (
            "Attend one seminar and become a fully proficient professional."
        )
    elif mutation == "invented_duration":
        pathway["total_hours"] = 999
    elif mutation == "forecast":
        result["scenarios"][0]["is_forecast"] = True
    elif mutation == "measured_sdg_impact":
        result["sdg_alignments"][0]["measured_impact"] = True
    elif mutation == "invented_approval":
        result["review"]["academic_approval"] = True
    else:
        pathway["citations"][0]["quote"] = "Invented source guarantees academic improvement."
    with pytest.raises((DomainError, ValueError)):
        validate_plan_result(result)


def test_sdg_target_uses_official_un_text_and_only_explicit_skill_scoped_proposals(
    session, database
):
    fixture = seed_pathways(session, database)
    result = evaluate(session, fixture)
    supported = [row for row in result.sdg_alignments if row.status == "possible_contribution"]
    assert len(supported) == 2
    assert all(row.goal_code == "4" and row.target_code == "4.4" for row in supported)
    assert all(row.goal_title == fixture.sdg_targets["4"].title for row in supported)
    assert all(row.target_title == fixture.sdg_targets["4.4"].title for row in supported)
    assert all(
        row.measured_impact is False and row.citations and row.rationale for row in supported
    )
    assert not any(
        row.recommendation_id in {fixture.by_skill["sql"].id, fixture.by_skill["governance"].id}
        and row.status == "possible_contribution"
        for row in result.sdg_alignments
    )


def test_missing_sdg_mapping_abstains_instead_of_automatic_educational_tagging(session, database):
    fixture = seed_pathways(session, database, include_sdgs=False)
    result = evaluate(session, fixture)
    assert result.sdg_alignments
    assert all(row.status in {"unmapped", "insufficient_evidence"} for row in result.sdg_alignments)
    assert all(row.goal_code is None and row.target_code is None for row in result.sdg_alignments)


@pytest.mark.parametrize(
    "mutation", ["unreviewed", "unsupported_mechanism", "wrong_skill_citation", "fabricated_quote"]
)
def test_unsupported_sdg_relationships_cannot_be_presented_as_possible_contributions(
    session, database, mutation
):
    fixture = seed_pathways(session, database)
    request = fixture.request.model_copy(deep=True)
    mapping = request.sdg_mappings[0]
    if mutation == "unreviewed":
        mapping.reviewed = False
    elif mutation == "unsupported_mechanism":
        mapping.mechanism = "resource_efficient_practice"
    elif mutation == "wrong_skill_citation":
        mapping.citations = request.sdg_mappings[1].citations
    else:
        mapping.citations[
            0
        ].quote = "Invented evidence says this programme has achieved SDG impact."
    try:
        result = evaluate(session, fixture, request)
    except (DomainError, ValueError):
        return
    assert not any(
        row.recommendation_id == mapping.recommendation_id and row.status == "possible_contribution"
        for row in result.sdg_alignments
    )


def test_pydantic_rejects_future_cutoffs_duplicate_scenarios_and_forecast_fields(session, database):
    fixture = seed_pathways(session, database)
    payload = fixture.request.model_dump(mode="json")
    with pytest.raises(ValidationError):
        PlanRequest.model_validate(
            {**payload, "as_of": (datetime.now(UTC) + timedelta(days=1)).isoformat()}
        )
    with pytest.raises(ValidationError, match="distinct"):
        PlanRequest.model_validate({**payload, "scenarios": [payload["scenarios"][0]] * 2})
    payload["scenarios"][0]["employment_growth"] = 999
    with pytest.raises(ValidationError, match="Extra inputs"):
        PlanRequest.model_validate(payload)
