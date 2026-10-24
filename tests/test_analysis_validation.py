"""Bounded output grounding; all sources/courses in these tests are synthetic."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from shiftos.schemas.analysis import (
    DIMENSIONS,
    AnalysisRequest,
    CourseEvidence,
    EvidenceItem,
    EvidencePacket,
    ProgrammeResult,
    RightsDecision,
)
from shiftos.services.analysis.providers import _claude_transport_schema
from shiftos.services.analysis.validation import (
    assemble_result,
    offline_result,
    validate_result,
)


@pytest.fixture
def packet():
    ids = [uuid4() for _ in range(8)]
    reference = EvidenceItem(
        id=f"academic_standard:{ids[0]}",
        kind="academic_standard",
        record_id=ids[0],
        version_id=ids[1],
        evidence_reference_id=ids[2],
        source_id=ids[3],
        evidence_class="synthetic_demo",
        scope="academic_benchmark",
        source_url="https://example.invalid/synthetic",
        publisher="Synthetic Authority",
        title="Synthetic accounting benchmark",
        locator="Synthetic paragraph 1",
        excerpt="Synthetic accounting benchmark includes responsible professional conduct.",
        publication_date="2026-01-01",
        date_precision="day",
        retrieved_at=datetime.now(UTC),
        review_status="reviewed",
        is_synthetic=True,
        rights=RightsDecision(
            internal_analysis_allowed=True,
            external_model_allowed=True,
            excerpt_output_allowed=True,
            basis="Explicit synthetic fixture",
        ),
        internal_eligible=True,
        model_eligible=True,
    )
    courses = [
        CourseEvidence(
            id=uuid4(),
            name="Synthetic Financial Accounting",
            year=year,
            course_type="UNKNOWN",
            evidence_level="title_only",
            is_verified=False,
            needs_syllabus_confirmation=True,
            reference_ids=[reference.id],
        )
        for year in (1, 2)
    ]
    return EvidencePacket(
        programme_id=ids[4],
        programme_revision_id=ids[5],
        institution_id=ids[6],
        programme_name="Bachelor of Synthetic Accounting",
        discipline="accounting",
        is_synthetic=True,
        as_of=datetime.now(UTC),
        courses=courses,
        references=[reference],
        source_policy_hash="a" * 64,
        gaps=["syllabus_confirmation_required"],
    )


def test_offline_result_is_deterministic_complete_and_preliminary(packet):
    result = offline_result(packet)
    assert result == offline_result(packet)
    assert result.result_mode == "offline_synthetic"
    assert len(result.courses) == len(packet.courses) == 2
    assert result.summary.insufficient_evidence_count == 2
    assert not result.insights.verified_curriculum_evidence
    assert result.insights.review_course_ids == [course.id for course in packet.courses]
    for course in result.courses:
        assert course.needs_syllabus_confirmation
        assert course.is_final_curriculum_verdict is False
        assert all(getattr(course, name).status == "insufficient_evidence" for name in DIMENSIONS)


@pytest.mark.parametrize(
    "change", ["unknown_reference", "fabricated_quote", "other_scope", "other_course_reference"]
)
def test_fabricated_unassociated_or_mis_scoped_citations_fail(packet, change):
    payload = offline_result(packet).model_dump(mode="json")
    citation = payload["courses"][0]["foundational_relevance"]["citations"][0]
    if change == "unknown_reference":
        citation["reference_id"] = "source:invented"
    elif change == "fabricated_quote":
        citation["quote"] = "This course teaches every skill required by industry."
    elif change == "other_scope":
        citation["scope"] = "verified_syllabus"
    else:
        packet.courses[0].reference_ids = []
    with pytest.raises(ValueError):
        validate_result(payload, packet)


def test_transport_required_fields_do_not_relax_citation_or_privacy_validation(packet):
    transport_schema = _claude_transport_schema(ProgrammeResult.model_json_schema())
    payload = offline_result(packet).model_dump(mode="json")

    assert set(transport_schema["required"]) == set(transport_schema["properties"])
    assert validate_result(payload, packet)

    fabricated = deepcopy(payload)
    citation = fabricated["courses"][0]["foundational_relevance"]["citations"][0]
    citation["quote"] = "This synthetic course teaches every skill."
    with pytest.raises(ValueError, match="Quote does not match"):
        validate_result(fabricated, packet)

    restricted_packet = packet.model_copy(deep=True)
    restricted_packet.references[0].rights.external_model_allowed = False
    with pytest.raises(ValueError, match="permission"):
        validate_result(payload, restricted_packet)


@pytest.mark.parametrize(
    "change", ["missing", "extra", "duplicate", "renamed", "promoted", "final_verdict"]
)
def test_model_cannot_change_frozen_inventory_or_verification(packet, change):
    payload = offline_result(packet).model_dump(mode="json")
    if change == "missing":
        payload["courses"].pop()
    elif change == "extra":
        extra = deepcopy(payload["courses"][0])
        extra["course_id"] = str(uuid4())
        payload["courses"].append(extra)
    elif change == "duplicate":
        payload["courses"].append(deepcopy(payload["courses"][0]))
    elif change == "renamed":
        payload["courses"][0]["course_name"] = "Invented Course"
    elif change == "promoted":
        payload["courses"][0]["evidence_level"] = "detailed_syllabus"
    else:
        payload["courses"][0]["is_final_curriculum_verdict"] = True
    with pytest.raises(ValueError):
        validate_result(payload, packet)


@pytest.mark.parametrize(
    "field,value",
    [
        ("score", 0.99),
        ("obsolete", True),
        ("replacement", "Remove this course"),
        ("teaching_claim", "XMUM teaches auditing"),
        ("sources", ["https://invented.invalid"]),
    ],
)
def test_no_schema_path_for_scores_obsolescence_actions_or_free_factual_prose(packet, field, value):
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0][field] = value
    with pytest.raises(ValidationError):
        validate_result(payload, packet)


@pytest.mark.parametrize(
    "name", ["foundational_relevance", "curriculum_currency", "future_resilience"]
)
def test_title_only_cannot_establish_content_dimensions_even_with_benchmark(packet, name):
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0][name]["status"] = "investigate"
    with pytest.raises(ValueError, match="Unconfirmed content"):
        validate_result(payload, packet)


def test_benchmark_requires_not_teaching_limitation(packet):
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0]["foundational_relevance"]["limitations"].remove(
        "benchmark_not_teaching_evidence"
    )
    with pytest.raises(ValueError, match="benchmarks"):
        validate_result(payload, packet)


@pytest.mark.parametrize(
    "property,value,limitation",
    [
        ("review_status", "needs_review", "structured_source_needs_review"),
        ("date_precision", "unknown", "unknown_source_date"),
        ("historical_context_only", True, "historical_evidence"),
    ],
)
def test_model_cannot_hide_source_review_or_date_uncertainty(packet, property, value, limitation):
    setattr(packet.references[0], property, value)
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0]["foundational_relevance"]["limitations"].remove(limitation)
    with pytest.raises(ValueError, match="preserve source"):
        validate_result(payload, packet)


@pytest.mark.parametrize(
    "permission", ["internal_analysis_allowed", "external_model_allowed", "excerpt_output_allowed"]
)
def test_permission_revocation_prevents_citing_already_known_excerpt(packet, permission):
    payload = offline_result(packet).model_dump(mode="json")
    setattr(packet.references[0].rights, permission, False)
    with pytest.raises(ValueError, match="permission"):
        validate_result(payload, packet)


def test_substantive_status_without_citations_is_rejected(packet):
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0]["ai_transformation"]["status"] = "investigate"
    with pytest.raises(ValueError, match="requires admissible citations"):
        validate_result(payload, packet)


def test_ai_exposure_never_promotes_to_task_transformation(packet):
    item = packet.references[0]
    item.kind, item.scope = "ai_evidence", "ai_exposure_context"
    item.facts = {"impact_type": "occupational_exposure"}
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0]["ai_transformation"]["status"] = "investigate"
    with pytest.raises(ValueError, match="AI transformation"):
        validate_result(payload, packet)


def test_ai_reviewed_observed_identity_can_support_investigation_without_teaching_claim(packet):
    item = packet.references[0]
    item.kind, item.scope = "ai_evidence", "ai_task_context"
    item.identity_reviewed = True
    item.facts = {"impact_type": "observed_practice"}
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0]["ai_transformation"]["status"] = "investigate"
    result = validate_result(payload, packet)
    assert result.courses[0].ai_transformation.status == "investigate"
    assert result.courses[0].needs_syllabus_confirmation
    assert result.insights.ai_task_developments


def test_broad_group_advertising_cannot_establish_individual_course_alignment(packet):
    item = packet.references[0]
    item.kind, item.scope = "workforce", "workforce_context"
    item.facts = {"population_level": "occupation_group"}
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0]["workforce_alignment"]["status"] = "investigate"
    with pytest.raises(ValueError, match="workforce alignment"):
        validate_result(payload, packet)


def test_free_question_prose_cannot_hide_an_unsupported_teaching_assertion(packet):
    payload = offline_result(packet).model_dump(mode="json")
    payload["courses"][0]["curriculum_currency"]["review_questions"] = [
        "Review whether XMUM's obsolete auditing course should be removed."
    ]
    with pytest.raises(ValidationError):
        validate_result(payload, packet)


def test_programme_insights_are_derived_and_untrusted_model_aggregation_is_discarded(packet):
    payload = offline_result(packet).model_dump(mode="json")
    payload["insights"]["demand_context"] = [{"fabricated_forecast": 999}]
    payload["insights"]["unknowns"] = ["Pretend everything is verified"]
    result = validate_result(payload, packet)
    assert result.insights.demand_context == []
    assert result.insights.unknowns == packet.gaps


def test_programme_summary_cannot_misrepresent_coverage(packet):
    payload = offline_result(packet).model_dump(mode="json")
    payload["summary"]["insufficient_evidence_count"] = 0
    with pytest.raises(ValueError, match="summary counts"):
        validate_result(payload, packet)


def test_real_offline_processing_is_explicit_deterministic_insufficiency(packet):
    packet.is_synthetic = False
    for reference in packet.references:
        reference.is_synthetic = False
        reference.evidence_class = "published_standard"
    result = offline_result(packet)
    assert result.result_mode == "deterministic_insufficiency"
    assert not result.is_synthetic
    payload = result.model_dump(mode="json")
    payload["result_mode"] = "offline_synthetic"
    with pytest.raises(ValueError, match="real programme"):
        validate_result(payload, packet)


def test_batch_packet_aggregation_keeps_exact_chunk_inventory(packet):
    packet.courses = packet.courses[:1]
    result = offline_result(packet)
    assert assemble_result(packet, result.courses, "live_model").summary.returned_count == 1
    assert validate_result(result.model_dump(mode="json"), packet).summary.inventory_count == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"as_of": "2026-10-01T00:00:00"},
        {"as_of": datetime.now(UTC) + timedelta(days=2)},
        {"idempotency_key": "invalid key"},
        {"mode": "fake-live"},
        {"research_url": "https://unapproved.invalid"},
    ],
)
def test_analysis_request_rejects_bad_cutoffs_keys_or_unapproved_fields(changes):
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(changes)
