"""Ground structured source quotes and safe questions, not arbitrary prose semantics.

The model selects evidence, a qualitative review status, and fixed question
templates. It cannot supply free factual paraphrases, scores, curricular verdicts,
new sources, workforce arithmetic, actions or recommendations in this contract.
This is a deliberately narrow, auditable screening vocabulary, not a claim that
general natural-language entailment has been solved deterministically.
"""

from shiftos.schemas.analysis import (
    DIMENSIONS,
    Citation,
    CourseFindingResult,
    DimensionFinding,
    EvidencePacket,
    ProgrammeInsights,
    ProgrammeResult,
    ProgrammeSummary,
)

SCOPE_BY_DIMENSION = {
    "foundational_relevance": {"academic_benchmark", "occupation_benchmark", "verified_syllabus"},
    "ai_transformation": {"ai_task_context", "ai_exposure_context", "verified_syllabus"},
    "workforce_alignment": {"occupation_benchmark", "workforce_context", "verified_syllabus"},
    "curriculum_currency": {
        "academic_benchmark",
        "ai_task_context",
        "occupation_benchmark",
        "verified_syllabus",
    },
    "future_resilience": {
        "academic_benchmark",
        "occupation_benchmark",
        "ai_task_context",
        "verified_syllabus",
    },
}
CONTENT_DIMENSIONS = {"foundational_relevance", "curriculum_currency", "future_resilience"}
QUESTION_BY_DIMENSION = {
    "foundational_relevance": (
        "Confirm the intended foundational educational purpose with academic reviewers."
    ),
    "ai_transformation": (
        "Review whether assessments require critical evaluation of AI-assisted task outputs."
    ),
    "workforce_alignment": (
        "Confirm whether a reviewed Malaysian occupation crosswalk "
        "and suitable demand observations are available."
    ),
    "curriculum_currency": (
        "Confirm whether current syllabus evidence addresses the cited knowledge expectation."
    ),
    "future_resilience": (
        "Review whether transferable judgement and communication skills are assessed."
    ),
}


def _normal(value: str) -> str:
    return " ".join(value.split())


def _required_limitations(item) -> set[str]:
    """Expose scope constraints in the finding as well as the frozen provenance."""
    required = set()
    if item.review_status == "needs_review":
        required.add("structured_source_needs_review")
    if item.date_precision == "unknown":
        required.add("unknown_source_date")
    if item.historical_context_only:
        required.add("historical_evidence")
    if item.scope == "academic_benchmark":
        required.add("benchmark_not_teaching_evidence")
    if item.scope in {"ai_task_context", "ai_exposure_context"}:
        required.add("model_or_study_scope_limited")
    if item.scope == "ai_exposure_context":
        required.add("exposure_not_replacement_probability")
    if item.scope == "workforce_context" and item.facts.get("population_level") != "occupation":
        required.add("broad_population_not_individual_demand")
    return required


def _insights(packet: EvidencePacket, courses: list[CourseFindingResult]) -> ProgrammeInsights:
    references = {reference.id: reference for reference in packet.references}
    questions, verified, ai = {}, {}, {}
    for course in courses:
        for dimension in DIMENSIONS:
            finding = getattr(course, dimension)
            for question in finding.review_questions:
                questions[question] = None
            for citation in finding.citations:
                reference = references.get(citation.reference_id)
                if reference is None:
                    continue
                identity = (citation.reference_id, citation.quote)
                if reference.scope == "verified_syllabus":
                    verified[identity] = citation
                if reference.scope == "ai_task_context":
                    ai[identity] = citation
    return ProgrammeInsights(
        verified_curriculum_evidence=list(verified.values()),
        ai_task_developments=list(ai.values()),
        potential_coverage_questions=list(questions),
        review_course_ids=[
            course.course_id
            for course in courses
            if course.review_flag != "monitor" or course.needs_syllabus_confirmation
        ],
        demand_context=packet.radar,
        unknowns=packet.gaps,
    )


def assemble_result(
    packet: EvidencePacket,
    courses: list[CourseFindingResult],
    result_mode: str,
) -> ProgrammeResult:
    """Aggregate counts and programme questions without model-generated facts/math."""
    return ProgrammeResult(
        programme_revision_id=packet.programme_revision_id,
        is_synthetic=packet.is_synthetic,
        result_mode=result_mode,
        courses=courses,
        summary=ProgrammeSummary(
            inventory_count=len(packet.courses),
            returned_count=len(courses),
            review_required_count=sum(
                course.review_flag != "monitor" or course.needs_syllabus_confirmation
                for course in courses
            ),
            insufficient_evidence_count=sum(
                any(
                    getattr(course, dimension).status == "insufficient_evidence"
                    for dimension in DIMENSIONS
                )
                for course in courses
            ),
        ),
        insights=_insights(packet, courses),
    )


def validate_result(payload: dict, packet: EvidencePacket) -> ProgrammeResult:
    result = ProgrammeResult.model_validate(payload)
    if (
        result.programme_revision_id != packet.programme_revision_id
        or result.is_synthetic != packet.is_synthetic
    ):
        raise ValueError("Result revision or synthetic lane does not match frozen evidence")
    if result.result_mode == "offline_synthetic" and not packet.is_synthetic:
        raise ValueError("A real programme cannot be reported as a synthetic offline evaluation")
    inventory = {course.id: course for course in packet.courses}
    ids = [course.course_id for course in result.courses]
    if len(ids) != len(set(ids)) or set(ids) != set(inventory):
        raise ValueError(
            "Result must contain every frozen course exactly once and no extra courses"
        )
    references = {item.id: item for item in packet.references}
    if len(references) != len(packet.references):
        raise ValueError("Frozen evidence contains duplicate reference identities")
    for course in result.courses:
        original = inventory[course.course_id]
        if course.course_name != original.name or course.evidence_level != original.evidence_level:
            raise ValueError("Result changes a frozen course name or evidence level")
        if course.needs_syllabus_confirmation != original.needs_syllabus_confirmation:
            raise ValueError("Result changes the documented syllabus-confirmation requirement")
        if original.needs_syllabus_confirmation and course.review_flag == "monitor":
            raise ValueError(
                "Unconfirmed curriculum content cannot receive an unconditional monitor flag"
            )
        for name in DIMENSIONS:
            finding = getattr(course, name)
            seen = set()
            for citation in finding.citations:
                item = references.get(citation.reference_id)
                if item is None or citation.reference_id not in original.reference_ids:
                    raise ValueError("Citation is not an associated frozen evidence reference")
                if (
                    not item.model_eligible
                    or not item.internal_eligible
                    or not all(
                        (
                            item.rights.internal_analysis_allowed,
                            item.rights.external_model_allowed,
                            item.rights.excerpt_output_allowed,
                        )
                    )
                ):
                    raise ValueError(
                        "Citation lacks explicit admission/processing/output permission"
                    )
                if item.is_synthetic != packet.is_synthetic or item.review_status == "rejected":
                    raise ValueError("Citation is rejected or belongs to another evidence lane")
                if item.scope != citation.scope or item.scope not in SCOPE_BY_DIMENSION[name]:
                    raise ValueError("Citation scope cannot support this dimension")
                if len(_normal(citation.quote)) < 8 or _normal(citation.quote) not in _normal(
                    item.excerpt
                ):
                    raise ValueError("Quote does not match its admitted source excerpt")
                identity = (citation.reference_id, _normal(citation.quote))
                if identity in seen:
                    raise ValueError("Duplicate citation")
                seen.add(identity)
            if finding.status != "insufficient_evidence" and not finding.citations:
                raise ValueError("A substantive review status requires admissible citations")
            if not finding.review_questions:
                raise ValueError(
                    "Each screening dimension requires an explicit safe review question"
                )
            if original.needs_syllabus_confirmation:
                if "needs_syllabus_confirmation" not in finding.limitations:
                    raise ValueError(
                        "Title/unconfirmed content must retain syllabus-confirmation limitation"
                    )
                if name in CONTENT_DIMENSIONS and finding.status != "insufficient_evidence":
                    raise ValueError(
                        "Unconfirmed content cannot establish foundational purpose, "
                        "currency or resilience"
                    )
            if name == "ai_transformation" and finding.status != "insufficient_evidence":
                if not any(
                    references[c.reference_id].scope == "ai_task_context"
                    and references[c.reference_id].identity_reviewed
                    and references[c.reference_id].review_status == "reviewed"
                    and not references[c.reference_id].historical_context_only
                    for c in finding.citations
                ):
                    raise ValueError(
                        "AI transformation requires reviewed, dated task capability "
                        "and exact occupation identity"
                    )
            if name == "workforce_alignment" and finding.status != "insufficient_evidence":
                if not any(
                    references[c.reference_id].scope == "workforce_context"
                    and references[c.reference_id].identity_reviewed
                    and references[c.reference_id].facts.get("population_level") == "occupation"
                    and not references[c.reference_id].historical_context_only
                    for c in finding.citations
                ):
                    raise ValueError(
                        "Individual workforce alignment needs reviewed identity "
                        "and granular observations"
                    )
            if (
                any(
                    references[c.reference_id].scope == "ai_exposure_context"
                    for c in finding.citations
                )
                and "exposure_not_replacement_probability" not in finding.limitations
            ):
                raise ValueError(
                    "Exposure/forecast citations must preserve non-replacement limitation"
                )
            if (
                any(
                    references[c.reference_id].scope == "academic_benchmark"
                    for c in finding.citations
                )
                and "benchmark_not_teaching_evidence" not in finding.limitations
            ):
                raise ValueError(
                    "Academic benchmarks must not be presented as university teaching evidence"
                )
            required = set().union(
                *(_required_limitations(references[c.reference_id]) for c in finding.citations)
            )
            if not required.issubset(finding.limitations):
                raise ValueError(
                    "Citations must preserve source date, review and scope limitations"
                )
    rebuilt = assemble_result(packet, result.courses, result.result_mode)
    if result.summary != rebuilt.summary:
        raise ValueError("Programme summary counts do not match its course findings")
    # All programme-level information is derived, even if the model proposed insights.
    return rebuilt


def offline_result(packet: EvidencePacket) -> ProgrammeResult:
    """A labelled fixture evaluator or honest deterministic abstention, never fake Gemini."""
    courses = []
    references = {item.id: item for item in packet.references if item.model_eligible}
    for course in packet.courses:
        dimensions = {}
        for dimension in DIMENSIONS:
            eligible = [
                references[key]
                for key in course.reference_ids
                if key in references and references[key].scope in SCOPE_BY_DIMENSION[dimension]
            ]
            citations = [
                Citation(reference_id=item.id, quote=item.excerpt[:1500], scope=item.scope)
                for item in eligible[:2]
                if len(item.excerpt.strip()) >= 8
            ]
            limitations = (
                ["no_admissible_evidence"]
                if not citations
                else ["candidate_match_not_identity", "engineering_review_not_academic_approval"]
            )
            limitations.append(
                "offline_synthetic" if packet.is_synthetic else "live_model_not_used"
            )
            if course.needs_syllabus_confirmation:
                limitations.extend(["needs_syllabus_confirmation", "title_only_not_taught_content"])
            if any(item.scope == "ai_exposure_context" for item in eligible[:2]):
                limitations.append("exposure_not_replacement_probability")
            if any(item.scope == "academic_benchmark" for item in eligible[:2]):
                limitations.append("benchmark_not_teaching_evidence")
            for citation in citations:
                limitations.extend(sorted(_required_limitations(references[citation.reference_id])))
            dimensions[dimension] = DimensionFinding(
                status="insufficient_evidence",
                citations=citations,
                review_questions=[QUESTION_BY_DIMENSION[dimension]],
                limitations=list(dict.fromkeys(limitations)),
            )
        courses.append(
            CourseFindingResult(
                course_id=course.id,
                course_name=course.name,
                evidence_level=course.evidence_level,
                needs_syllabus_confirmation=course.needs_syllabus_confirmation,
                review_flag="needs_syllabus_confirmation"
                if course.needs_syllabus_confirmation
                else "insufficient_evidence",
                **dimensions,
            )
        )
    result = assemble_result(
        packet,
        courses,
        "offline_synthetic" if packet.is_synthetic else "deterministic_insufficiency",
    )
    return validate_result(result.model_dump(mode="json"), packet)
