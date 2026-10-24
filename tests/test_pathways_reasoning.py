"""Mocked optional Claude assistance: no network and no change to canonical decisions."""

from copy import deepcopy

import pytest
from pathways_helpers import seed_pathways
from test_analysis_claude_provider import configured

from shiftos.services.analysis.providers import ProviderError
from shiftos.services.pathways.engine import evaluate, validate_plan_result
from shiftos.services.pathways.reasoning import INSTRUCTION, explain


@pytest.fixture
def plan(session, database):
    fixture = seed_pathways(session, database)
    return evaluate(session, fixture.parent.id, fixture.request, fixture.settings, fixture.now)


def raw_choices(plan):
    return {
        "choices": [
            {
                "pathway_key": row.key,
                "scenario_key": "accelerated_ai_adoption",
                "review_question": "Confirm the proposed activity and its assessment evidence.",
                "citations": [row.citations[0].model_dump(mode="json")],
            }
            for row in plan.pathways
            if row.citations
        ]
    }


def factory(raw, seen, model="claude-opus-5", failure=False):
    class MockClaude:
        def __init__(self, settings):
            assert (
                settings.analysis_provider_max_attempts
                == settings.analysis_validation_max_attempts
                == 1
            )
            assert settings.claude_max_output_tokens <= 4096
            assert settings.analysis_provider_timeout_seconds <= 60
            assert not settings.gemini_enabled and not settings.research_enabled
            self.last_response_metadata = {
                "actual_model": model,
                "request_count": 1,
                "usage": {"input_tokens": 23, "output_tokens": 11},
            }

        def generate(self, packet, schema, *, task_instruction):
            assert task_instruction == INSTRUCTION
            seen.append(deepcopy(packet))
            if failure:
                raise ProviderError("provider_unavailable", "Synthetic unavailable response")
            return deepcopy(raw)

    return MockClaude


@pytest.mark.parametrize(
    "gate",
    [
        "consent",
        "provider",
        "disabled",
        "rights",
        "model_rights",
        "no_pathways",
        "missing_citation",
    ],
)
def test_model_is_never_constructed_without_all_gates(plan, gate):
    settings = configured(analysis_model_provider="replit_claude")
    if gate == "consent":
        settings.analysis_external_processing_allowed = False
    elif gate == "provider":
        settings.analysis_model_provider = "none"
    elif gate == "disabled":
        settings.claude_enabled = False
    elif gate == "rights":
        plan.evidence[0].rights.external_model_allowed = False
    elif gate == "model_rights":
        plan.evidence[0].model_eligible = False
    elif gate == "no_pathways":
        plan.pathways = []
    else:
        plan.pathways[0].citations[0].quote = "Unsupported quotation"

    def forbidden(*args, **kwargs):
        pytest.fail("Source/consent failure must not initialise a provider")

    result = explain(plan, settings, provider_factory=forbidden)
    assert result.model["request_count"] == 0
    assert result.pathways == plan.pathways


def test_valid_mocked_claude_review_preserves_every_canonical_field(plan):
    seen = []
    result = explain(
        plan,
        configured(analysis_model_provider="replit_claude"),
        provider_factory=factory(raw_choices(plan), seen),
    )
    assert len(seen) == 1
    assert result.model["status"] == "validated_pathway_review"
    assert result.model["usage"] == {"input_tokens": 23, "output_tokens": 11}
    assert result.model["observed_cost"] is None
    assert result.model_dump(exclude={"model"}) == plan.model_dump(exclude={"model"})
    validate_plan_result(result)


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "unknown", "quote", "new_fact", "wrong_model", "timeout"]
)
def test_invalid_mocked_review_is_rejected_without_repair(plan, fault):
    raw, seen = raw_choices(plan), []
    if fault == "missing":
        raw["choices"].pop()
    elif fault == "duplicate":
        raw["choices"].append(deepcopy(raw["choices"][0]))
    elif fault == "unknown":
        raw["choices"][0]["pathway_key"] = "fabricated-path"
    elif fault == "quote":
        raw["choices"][0]["citations"][0]["quote"] = "Invented claim"
    elif fault == "new_fact":
        raw["choices"][0]["achieved_competence"] = True
    result = explain(
        plan,
        configured(analysis_model_provider="replit_claude"),
        provider_factory=factory(
            raw,
            seen,
            model="unexpected" if fault == "wrong_model" else "claude-opus-5",
            failure=fault == "timeout",
        ),
    )
    assert len(seen) == 1
    assert result.model["status"] == "review_unavailable"
    assert result.pathways == plan.pathways and result.scenarios == plan.scenarios
    assert result.model["observed_cost"] is None
