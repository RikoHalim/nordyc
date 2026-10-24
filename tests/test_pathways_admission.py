"""Original resource provenance and scenario identities cannot be promoted by labels."""

from datetime import timedelta

import pytest
from pathways_helpers import seed_pathways
from pydantic import ValidationError

from shiftos.core.enums import EvidenceClass
from shiftos.core.errors import DomainError
from shiftos.models import Dataset, DatasetVersion, EvidenceReference, Source
from shiftos.schemas.career import CareerResult
from shiftos.schemas.pathways import ScenarioInput
from shiftos.services.pathways.engine import evaluate
from shiftos.services.pathways.resources import admit_resources


def test_inference_cannot_become_verified_original_resource(session, database):
    fixture = seed_pathways(session, database)
    source = fixture.resource_sources["model-workbook"]
    version = fixture.resource_versions["model-workbook"]
    reference = fixture.resources["model-workbook"]
    dataset = session.get(Dataset, version.dataset_id)
    source.evidence_class = EvidenceClass.INFERENCE
    for row in (source, version, reference, dataset):
        row.is_synthetic = False
    session.commit()
    resources, evidence, limitations = admit_resources(
        session,
        fixture.request.resources,
        CareerResult.model_validate(fixture.parent.result_json),
        fixture.settings,
        fixture.now,
    )
    assert all(row.reference_id != f"learning_resource:{reference.id}" for row in resources)
    assert all(row.evidence_reference_id != reference.id for row in evidence)
    assert "resource_inference_is_not_original_verification" in limitations


@pytest.mark.parametrize(
    "key,assumption",
    [
        ("accelerated_ai_adoption", "prioritise_incremental_coverage"),
        ("gradual_workforce_transformation", "prioritise_assessment_review"),
    ],
)
def test_scenario_label_cannot_reverse_its_assumption(key, assumption):
    with pytest.raises(ValidationError, match="distinct planning assumption"):
        ScenarioInput(key=key, assumption=assumption, rationale="Explicit test assumption.")


@pytest.mark.parametrize("fault", ["quote", "locator", "url", "publisher"])
def test_official_sdg_citation_and_attribution_cannot_be_substituted(session, database, fault):
    fixture = seed_pathways(session, database)
    target = session.get(type(fixture.sdg_targets["4.4"]), fixture.sdg_targets["4.4"].id)
    reference = session.get(EvidenceReference, target.evidence_id)
    version = session.get(DatasetVersion, target.version_id)
    source = session.get(Source, version.source_id)
    if fault == "quote":
        reference.excerpt = "Spurious words attributed to the United Nations."
    elif fault == "locator":
        reference.locator = "A fabricated source page"
    elif fault == "url":
        source.url = "https://example.com/unverified-copy"
    else:
        source.publisher = "An unrelated publisher"
    session.commit()
    with pytest.raises(DomainError, match="UN"):
        evaluate(session, fixture.parent.id, fixture.request, fixture.settings, fixture.now)


def test_parent_sdg_goal_rights_are_admitted_separately_from_target(session, database):
    fixture = seed_pathways(session, database)
    goal = session.get(type(fixture.sdg_targets["4"]), fixture.sdg_targets["4"].id)
    reference = session.get(EvidenceReference, goal.evidence_id)
    reference.metadata_json = {**reference.metadata_json, "rights_withdrawn": True}
    session.commit()
    result = evaluate(session, fixture.parent.id, fixture.request, fixture.settings, fixture.now)
    assert not any(row.status == "possible_contribution" for row in result.sdg_alignments)
    assert "sdg_parent_goal_not_admissible" in result.limitations


def test_later_plan_cutoff_does_not_refresh_frozen_ai_observation_age(session, database):
    from shiftos.services.pathways.scenarios import build_scenarios

    fixture = seed_pathways(session, database, observed_ai=True)
    result = evaluate(session, fixture.parent.id, fixture.request, fixture.settings, fixture.now)
    assert result.comparison.changed_recommendation_ids
    scenarios, comparison = build_scenarios(
        result.career,
        result.recommendations,
        result.evidence,
        result.inputs.scenarios,
        result.as_of + timedelta(days=731),
    )
    assert not comparison.changed_recommendation_ids
    assert not any(
        priority.priority == "conditional_priority"
        for scenario in scenarios
        for priority in scenario.priorities
    )
