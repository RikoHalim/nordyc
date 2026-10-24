"""Frozen output constraints over fictional evidence; never live model results."""

import httpx
import pytest
from career_helpers import career_settings, seed_career

from shiftos.services.career.engine import evaluate, validate_career_result


@pytest.fixture
def evaluated(session, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Output validation tests cannot make any external request")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    fixture = seed_career(session)
    result = evaluate(
        session,
        fixture.programme.id,
        fixture.revision.id,
        fixture.request,
        career_settings(),
        fixture.now,
    )
    return fixture, result


def test_unknown_requirement_cannot_justify_a_forged_substantive_recommendation(evaluated):
    fixture, result = evaluated
    forged = result.model_copy(deep=True)
    recommendation = next(
        row for row in forged.recommendations if row.skill_id == fixture.skills["governance"].id
    )
    assert recommendation.citations  # Real fixture citations alone do not establish eligibility.
    recommendation.evidence_sufficiency = "supported"
    recommendation.category = "propose_elective"
    recommendation.priority = "supported_need"
    with pytest.raises(ValueError, match="deterministic eligible interventions"):
        validate_career_result(forged)


@pytest.mark.parametrize("field", ["action", "alternatives", "priority_basis"])
def test_valid_citations_do_not_authorize_changes_to_deterministic_actions(evaluated, field):
    _, result = evaluated
    forged = result.model_copy(deep=True)
    recommendation = forged.recommendations[0]
    if field == "alternatives":
        recommendation.alternatives[0].category = "propose_elective"
    else:
        setattr(
            recommendation,
            field,
            "Fabricated intervention or justification without source support.",
        )
    with pytest.raises(ValueError, match="deterministic eligible interventions"):
        validate_career_result(forged)


def test_occupation_status_cannot_be_promoted_without_demonstrated_essential_coverage(evaluated):
    fixture, result = evaluated
    forged = result.model_copy(deep=True)
    occupation = next(
        row for row in forged.occupations if row.occupation_id == fixture.occupations["steward"].id
    )
    assert occupation.status != "supported"
    occupation.status = "supported"
    with pytest.raises(ValueError, match="alignment status"):
        validate_career_result(forged)


def test_programme_status_cannot_be_promoted_from_partial_to_supported(evaluated):
    _, result = evaluated
    forged = result.model_copy(deep=True)
    assert forged.status == "partial"
    forged.status = "supported"
    with pytest.raises(ValueError, match="programme status"):
        validate_career_result(forged)


def test_unknown_requirement_cannot_be_promoted_to_partial_without_curriculum_support(evaluated):
    fixture, result = evaluated
    forged = result.model_copy(deep=True)
    for requirement in [
        *forged.competencies,
        *(row for occupation in forged.occupations for row in occupation.requirements),
    ]:
        if requirement.skill_id == fixture.skills["governance"].id:
            requirement.state = "partial"
            requirement.support_type = "documented_intent"
    with pytest.raises(ValueError, match="partial coverage"):
        validate_career_result(forged)


def test_separate_mock_model_choices_do_not_change_canonical_academic_output(evaluated):
    _, result = evaluated
    comparison = result.model_copy(deep=True)
    recommendation = next(row for row in comparison.recommendations if row.citations)
    comparison.model = {
        "status": "validated_option_comparison",
        "provider": "replit_claude",
        "request_count": 0,
        "choices": [
            {
                "recommendation_key": recommendation.key,
                "option_index": 0,
                "reason": "minimum_disruption",
                "review_question": (
                    "Review the evidence limitations before changing the curriculum."
                ),
                "citations": [recommendation.citations[0].model_dump(mode="json")],
            }
        ],
    }
    assert validate_career_result(comparison) == comparison
    assert comparison.recommendations == result.recommendations
