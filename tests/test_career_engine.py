"""Deterministic programme evidence acceptance; no model/search requests."""

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from career_helpers import career_settings, seed_career
from pydantic import ValidationError

from shiftos.core.enums import CourseType
from shiftos.core.errors import DomainError
from shiftos.models import AIImpactEvidence, EvidenceReference, WorkforceObservation
from shiftos.schemas.career import CareerRequest, CareerResult


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Career offline tests must not contact any external service")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def evaluate(session, fixture, request=None):
    from shiftos.services.career.engine import evaluate

    return evaluate(
        session,
        fixture.programme.id,
        fixture.revision.id,
        request or fixture.request,
        career_settings(),
        fixture.now,
    )


def requirements(result, fixture, skill):
    return [row for row in result.competencies if row.skill_id == fixture.skills[skill].id]


def test_synthetic_fixture_demonstrates_all_four_states_with_traceable_passages(session):
    fixture = seed_career(session)
    result = evaluate(session, fixture)
    assert CareerResult.model_validate(result.model_dump(mode="json")) == result
    assert result.is_synthetic and result.status in {"supported", "partial"}
    assert set(result.course_ids) == {row.id for row in fixture.courses.values()}
    assert len(result.occupations) == 3
    assert {row.state for row in requirements(result, fixture, "sql")} == {"supported"}
    assert {row.support_type for row in requirements(result, fixture, "sql")} == {"demonstrated"}
    assert {row.state for row in requirements(result, fixture, "model")} == {"partial"}
    assert {row.support_type for row in requirements(result, fixture, "model")} == {
        "documented_intent"
    }
    assert {row.state for row in requirements(result, fixture, "pipeline")} == {"partial"}
    assert {row.state for row in requirements(result, fixture, "security")} == {"documented_gap"}
    assert {row.state for row in requirements(result, fixture, "governance")} == {"unknown"}
    quotes = {row.id: row.excerpt for row in result.evidence}
    assert quotes
    for finding in result.competencies:
        assert finding.academic_review_required
        if finding.state != "unknown":
            assert finding.citations
        for citation in finding.citations:
            assert citation.reference_id in quotes
            assert citation.quote in quotes[citation.reference_id]


def test_demonstration_requires_separate_review_not_a_learning_outcome_label(session):
    fixture = seed_career(session)
    fixture.documents["query"].metadata_json = {
        **fixture.documents["query"].metadata_json,
        "demonstration_reviewed": False,
    }
    session.commit()
    result = evaluate(session, fixture)
    assert all(row.state != "supported" for row in requirements(result, fixture, "sql"))
    assert all(row.support_type != "demonstrated" for row in requirements(result, fixture, "sql"))


def test_documented_intent_never_becomes_demonstrated_attainment(session):
    fixture = seed_career(session)
    result = evaluate(session, fixture)
    for row in requirements(result, fixture, "model"):
        assert row.state == "partial" and row.support_type == "documented_intent"
        assert all(course.support != "demonstrated" for course in row.courses)


@pytest.mark.parametrize(
    "field,value",
    [
        ("reviewed", False),
        ("taxonomy", "Unrelated foreign taxonomy"),
        ("external_id", "wrong-occupation-identity"),
        ("discipline", "biotechnology"),
    ],
)
def test_unreviewed_or_incompatible_occupation_mapping_cannot_support_alignment(
    session, field, value
):
    fixture = seed_career(session)
    request = fixture.request.model_copy(deep=True)
    for mapping in request.mappings:
        setattr(mapping, field, value)
    if field in {"taxonomy", "external_id", "discipline"}:
        with pytest.raises(DomainError, match="identity|taxonomy|mapping|occupation|discipline"):
            evaluate(session, fixture, request)
        return
    result = evaluate(session, fixture, request)
    assert result.status == "insufficient_evidence"
    assert all(row.status == "insufficient_evidence" for row in result.occupations)
    assert all(row.rank is None and row.measure.value is None for row in result.occupations)


def test_no_occupation_mapping_abstains_despite_related_titles(session):
    fixture = seed_career(session)
    request = fixture.request.model_copy(update={"mappings": []})
    result = evaluate(session, fixture, request)
    assert result.status == "insufficient_evidence"
    assert not result.occupations or all(
        row.status == "insufficient_evidence" for row in result.occupations
    )


def test_missing_published_requirements_cannot_be_invented_from_occupation_title(session):
    fixture = seed_career(session)
    for relation in list(fixture.relationships.values()):
        session.delete(relation)
    session.commit()
    result = evaluate(session, fixture)
    assert not result.competencies
    assert all(
        row.status == "insufficient_evidence" and row.measure.value is None
        for row in result.occupations
    )


@pytest.mark.parametrize("relationship", ["related", "possible", "benchmark"])
def test_unknown_relationship_semantics_do_not_become_essential_requirements(session, relationship):
    fixture = seed_career(session)
    for relation in fixture.relationships.values():
        relation.relationship = relationship
    session.commit()
    result = evaluate(session, fixture)
    assert all(row.requirement_type == "unknown" for row in result.competencies)
    assert all(row.measure.value is None for row in result.occupations)


@pytest.mark.parametrize(
    "mutation", ["no_review", "wrong_quote", "wrong_course", "missing_content_review"]
)
def test_invalid_curriculum_support_is_not_admitted(session, mutation):
    fixture = seed_career(session)
    request = fixture.request.model_copy(deep=True)
    assertion = request.assertions[0]
    if mutation == "no_review":
        assertion.reviewed = False
    elif mutation == "wrong_quote":
        assertion.quote = "Invented proof of guaranteed professional proficiency."
    elif mutation == "wrong_course":
        assertion.course_id = fixture.courses["inventory"].id
    else:
        fixture.documents["query"].metadata_json = {
            **fixture.documents["query"].metadata_json,
            "content_reviewed": False,
        }
        session.commit()
    if mutation in {"wrong_quote", "wrong_course"}:
        with pytest.raises(DomainError):
            evaluate(session, fixture, request)
        return
    result = evaluate(session, fixture, request)
    assert all(row.state == "unknown" for row in requirements(result, fixture, "sql"))


@pytest.mark.parametrize(
    "mutation",
    ["incomplete_scope", "unreviewed", "no_completeness", "wrong_quote", "no_negative_claim"],
)
def test_confirmed_gap_requires_exact_reviewed_negative_evidence_for_entire_inventory(
    session, mutation
):
    fixture = seed_career(session)
    request = fixture.request.model_copy(deep=True)
    gap = request.gaps[0]
    if mutation == "incomplete_scope":
        gap.covered_course_ids = gap.covered_course_ids[:-1]
    elif mutation == "unreviewed":
        gap.reviewed = False
    elif mutation == "no_completeness":
        gap.completeness_confirmed = False
    elif mutation == "wrong_quote":
        gap.quote = "Fictional but unsupported universal absence claim."
    else:
        fixture.audit.metadata_json = {**fixture.audit.metadata_json, "negative_skill_ids": []}
        session.commit()
    if mutation == "wrong_quote":
        with pytest.raises(DomainError):
            evaluate(session, fixture, request)
        return
    result = evaluate(session, fixture, request)
    assert {row.state for row in requirements(result, fixture, "security")} == {"unknown"}
    assert not any(
        row.priority == "supported_need" and row.skill_id == fixture.skills["security"].id
        for row in result.recommendations
    )


def test_unassessed_competency_is_unknown_and_not_zero_in_a_percentage(session):
    fixture = seed_career(session)
    result = evaluate(session, fixture)
    steward = next(
        row for row in result.occupations if row.occupation_id == fixture.occupations["steward"].id
    )
    assert steward.measure.value is None
    assert steward.measure.unknown_requirements >= 1
    assert steward.measure.abstention_reason
    assert requirements(result, fixture, "governance")[0].evidence_needed


def test_optional_requirement_does_not_change_essential_denominator(session):
    fixture = seed_career(session)
    result = evaluate(session, fixture)
    analyst = next(
        row for row in result.occupations if row.occupation_id == fixture.occupations["analyst"].id
    )
    assert analyst.measure.denominator == 2
    assert analyst.measure.weights.get("essential") == 1.0
    assert analyst.measure.numerator <= analyst.measure.denominator
    assert analyst.measure.method_version == result.method_version


def test_complete_demonstrated_requirement_has_reproducible_positive_alignment(session):
    fixture = seed_career(session)
    result = evaluate(session, fixture)
    repeated = evaluate(session, fixture)
    practitioner = next(
        row
        for row in result.occupations
        if row.occupation_id == fixture.occupations["practitioner"].id
    )
    assert practitioner.status == "supported"
    assert practitioner.measure.denominator == practitioner.measure.numerator == 1
    assert practitioner.measure.value == 100
    assert result.model_dump(mode="json") == repeated.model_dump(mode="json")


@pytest.mark.parametrize("discipline", ["computing", "accounting", "biotechnology"])
def test_reviewed_cross_discipline_mapping_uses_passages_without_inventing_curriculum(
    session, discipline
):
    fixture = seed_career(session)
    fixture.programme.discipline_key = discipline
    fixture.programme.name = f"Bachelor of Synthetic {discipline.title()}"
    request = fixture.request.model_copy(deep=True)
    for occupation in fixture.occupations.values():
        occupation.metadata_json = {
            **occupation.metadata_json,
            "related_disciplines": [discipline],
            "scope_review": f"Fictional database competency benchmark for {discipline} only.",
        }
    for mapping in request.mappings:
        mapping.discipline = discipline
        mapping.basis = (
            f"Explicit fictional reviewer maps this {discipline} programme to the shared "
            "synthetic database benchmark using the stored assessment and syllabus passages; "
            "the programme title supplies no competency evidence."
        )
    session.commit()
    result = evaluate(session, fixture, request)
    practitioner = next(
        row
        for row in result.occupations
        if row.occupation_id == fixture.occupations["practitioner"].id
    )
    assert practitioner.status == "supported"
    assert practitioner.measure.value == 100
    assert practitioner.requirements[0].support_type == "demonstrated"
    assert practitioner.requirements[0].courses[0].course_id == fixture.courses["query"].id
    assert {row.state for row in requirements(result, fixture, "governance")} == {"unknown"}
    assert not any(
        support.course_id == fixture.courses["inventory"].id
        for row in result.competencies
        for support in row.courses
    )


@pytest.mark.parametrize("course_type", [CourseType.ELECTIVE, CourseType.UNKNOWN])
def test_noncompulsory_course_does_not_establish_universal_programme_coverage(session, course_type):
    fixture = seed_career(session)
    fixture.courses["query"].course_type = course_type
    session.commit()
    result = evaluate(session, fixture)
    practitioner = next(
        row
        for row in result.occupations
        if row.occupation_id == fixture.occupations["practitioner"].id
    )
    assert practitioner.status == "partial"
    assert practitioner.measure.value is None
    assert requirements(result, fixture, "sql")[0].state == "partial"
    assert requirements(result, fixture, "sql")[0].support_type == "demonstrated"
    assert all(
        course.extent == "partial"
        for row in requirements(result, fixture, "sql")
        for course in row.courses
    )


def test_incomparable_candidate_coverage_abstains_from_ranking(session):
    fixture = seed_career(session)
    result = evaluate(session, fixture)
    assert all(row.rank is None for row in result.occupations)
    assert result.ranking_basis


def test_recommendations_are_proportionate_cited_proposals_with_alternatives_and_no_change(session):
    fixture = seed_career(session)
    result = evaluate(session, fixture)
    assert result.recommendations
    for row in result.recommendations:
        assert row.programme_revision_id == fixture.revision.id
        assert row.academic_review_required and not row.automatic_curriculum_change
        assert row.minimum_sufficient_intervention and row.priority_basis and row.rationale
        assert row.alternatives and row.no_change_option.category == "no_change"
        assert row.citations or row.evidence_sufficiency == "insufficient_evidence"
        assert set(row.course_ids) <= set(result.course_ids)
        assert row.review_status in {"proposed", "needs_evidence"}
        assert not any(
            word in row.action.casefold() for word in ("remove course", "guaranteed employment")
        )
    gap_actions = [
        row for row in result.recommendations if row.skill_id == fixture.skills["security"].id
    ]
    assert gap_actions and any(row.priority == "supported_need" for row in gap_actions)


@pytest.mark.parametrize(
    "flag", ["rights_withdrawn", "internal_analysis_allowed", "excerpt_output_allowed"]
)
def test_source_permission_denials_override_synthetic_grants(session, flag):
    fixture = seed_career(session)
    if flag == "rights_withdrawn":
        fixture.version.metadata_json = {**fixture.version.metadata_json, flag: True}
    else:
        fixture.version.metadata_json = {
            **fixture.version.metadata_json,
            "analysis_permissions": {flag: False, "basis": "Synthetic permission withdrawn"},
        }
    session.commit()
    result = evaluate(session, fixture)
    assert all(row.status == "insufficient_evidence" for row in result.occupations)
    assert not result.competencies


def test_title_only_does_not_establish_content_or_a_gap_even_with_a_matching_skill_name(session):
    fixture = seed_career(session)
    request = fixture.request.model_copy(update={"assertions": [], "gaps": []})
    result = evaluate(session, fixture, request)
    assert result.competencies and all(row.state == "unknown" for row in result.competencies)
    assert all(row.measure.value is None for row in result.occupations)
    assert all(row.priority != "supported_need" for row in result.recommendations)


def test_future_review_cannot_supply_historical_cutoff_support(session):
    fixture = seed_career(session)
    request = fixture.request.model_copy(deep=True)
    for assertion in request.assertions:
        assertion.reviewed_at = fixture.now + timedelta(days=1)
    request.gaps[0].reviewed_at = fixture.now + timedelta(days=1)
    result = evaluate(session, fixture, request)
    assert all(row.state == "unknown" for row in result.competencies)


def test_pydantic_rejects_duplicate_mappings_and_future_analysis_cutoff(session):
    fixture = seed_career(session)
    payload = fixture.request.model_dump(mode="json")
    duplicated = deepcopy(payload)
    duplicated["mappings"].append(duplicated["mappings"][0])
    with pytest.raises(ValidationError, match="unique"):
        CareerRequest.model_validate(duplicated)
    payload["as_of"] = (fixture.now + timedelta(days=1)).isoformat()
    with pytest.raises(ValidationError, match="future"):
        CareerRequest.model_validate(payload)


def test_legacy_taxonomy_remains_historical_context_and_does_not_get_current_score(session):
    fixture = seed_career(session)
    fixture.version.publication_date = "2017-01-01"
    fixture.version.metadata_json = {
        **fixture.version.metadata_json,
        "edition": "Synthetic legacy 1.0.3",
        "language": "en",
    }
    session.commit()
    result = evaluate(session, fixture)
    assert result.status == "insufficient_evidence"
    assert all(row.measure.value is None and row.rank is None for row in result.occupations)
    pointers = [row for row in result.evidence if row.kind == "occupation"]
    assert pointers and all(row.publication_date == "2017-01-01" for row in pointers)
    assert all(row.historical_context_only for row in pointers)
    assert all(row.facts["edition"] == "Synthetic legacy 1.0.3" for row in pointers)
    assert all(row.facts["language"] == "en" for row in pointers)


@pytest.mark.parametrize("geography,years", [("MY", (2001, 2002)), ("GB", (2024, 2025))])
def test_workforce_scope_dates_and_deterministic_arithmetic_are_preserved(
    session, geography, years
):
    from shiftos.services.evidence.trends import compare_observations

    fixture = seed_career(session)
    occupation = fixture.occupations["practitioner"]
    observations = []
    for year, value in zip(years, ["100", "110"], strict=True):
        quote = f"Synthetic {geography} employment count {year}: {value}; no skill demand claim."
        reference = EvidenceReference(
            version_id=fixture.version.id,
            locator=f"synthetic:{geography}:{year}",
            excerpt=quote,
            review_status="reviewed",
            is_synthetic=True,
        )
        session.add(reference)
        session.flush()
        row = WorkforceObservation(
            version_id=fixture.version.id,
            evidence_id=reference.id,
            external_id=f"synthetic-{geography}-{year}",
            occupation_id=occupation.id,
            occupation_label=occupation.label,
            geography=geography,
            period_start=date(year, 1, 1),
            period_end=date(year, 12, 31),
            indicator="employment_count",
            value=Decimal(value),
            unit="persons",
            is_synthetic=True,
            metadata_json={
                "series_id": f"synthetic-series-{geography}",
                "population_level": "occupation",
            },
            limitations="Entirely fictional observed values; no Malaysian skill-demand inference.",
        )
        session.add(row)
        session.flush()
        observations.append(row)
    session.commit()
    expected = compare_observations(session, observations[0].id, observations[1].id)
    result = evaluate(session, fixture)
    alignment = next(row for row in result.occupations if row.occupation_id == occupation.id)
    assert len(alignment.workforce) == 1
    context = alignment.workforce[0]
    assert context["classification"] == expected.classification
    assert context["geography"] == geography
    assert context["period_end"] == f"{years[1]}-12-31"
    assert context["method"]["method_version"] == "workforce-radar-1"
    assert context["absolute_change"] == str(expected.absolute_change)
    assert context["percentage_change"] == str(expected.percentage_change)
    if years == (2001, 2002):
        assert context["historical_context_only"] is True
    pointers = [row for row in result.evidence if row.kind == "workforce"]
    assert {row.observation_start for row in pointers} == {f"{year}-01-01" for year in years}
    assert all(
        "occupation_observations_do_not_measure_skill_demand" in row.limitations for row in pointers
    )
    assert "taxonomy_does_not_establish_Malaysian_demand" in alignment.limitations


def test_ai_exposure_does_not_establish_observed_transformation_or_replacement(session):
    fixture = seed_career(session)
    reference = EvidenceReference(
        version_id=fixture.version.id,
        locator="synthetic:exposure",
        excerpt="Fictional occupational exposure estimate only; replacement is not established.",
        review_status="reviewed",
        is_synthetic=True,
    )
    session.add(reference)
    session.flush()
    session.add(
        AIImpactEvidence(
            version_id=fixture.version.id,
            evidence_id=reference.id,
            external_id=str(uuid4()),
            occupation_id=fixture.occupations["practitioner"].id,
            statement=reference.excerpt,
            impact_type="occupational_exposure",
            limitations="Synthetic exposure scenario, not observed capability.",
            is_synthetic=True,
        )
    )
    session.commit()
    result = evaluate(session, fixture)
    assert all(row.ai_transformation["is_ai_transforming"] is None for row in result.occupations)
    assert all(
        row.ai_transformation["status"] == "INSUFFICIENT_EVIDENCE" for row in result.occupations
    )
    assert all(
        "Exposure is not replacement probability." in row.ai_transformation["limitations"]
        for row in result.occupations
    )


@pytest.mark.parametrize("mutation", ["quote", "unknown_reference", "score", "cross_course"])
def test_frozen_result_validator_rejects_fabricated_citations_scores_and_scope(session, mutation):
    from shiftos.services.career.engine import validate_career_result

    fixture = seed_career(session)
    result = evaluate(session, fixture).model_dump(mode="json")
    if mutation == "quote":
        result["recommendations"][0]["citations"][0]["quote"] = "Fabricated academic certainty."
    elif mutation == "unknown_reference":
        result["recommendations"][0]["citations"][0]["reference_id"] = "unregistered-source"
    elif mutation == "score":
        practitioner = next(
            row
            for row in result["occupations"]
            if row["occupation_id"] == str(fixture.occupations["practitioner"].id)
        )
        practitioner["measure"]["value"] = 90
    else:
        result["recommendations"][0]["course_ids"] = [str(uuid4())]
    with pytest.raises(ValueError):
        validate_career_result(result)
