"""Frozen evidence and bounded screening contracts; never academic action authoring."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

SCHEMA_VERSION = "phase4-result-1"
POLICY_VERSION = "phase4-retrieval-1"
DIMENSIONS = (
    "foundational_relevance",
    "ai_transformation",
    "workforce_alignment",
    "curriculum_currency",
    "future_resilience",
)
Key = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")]
EvidenceLevel = Literal["title_only", "public_description", "detailed_syllabus", "missing"]
Scope = Literal[
    "academic_benchmark",
    "occupation_benchmark",
    "ai_task_context",
    "ai_exposure_context",
    "workforce_context",
    "university_inventory",
    "verified_syllabus",
]
ReviewQuestion = Literal[
    "Confirm which topics and assessments the syllabus actually documents.",
    "Review whether the cited benchmark applies to this programme and qualification.",
    "Review whether assessments require critical evaluation of AI-assisted task outputs.",
    "Confirm whether the cited occupation and tasks are relevant to this course.",
    "Review the cited study's model, date, task setting and limitations.",
    "Confirm whether current syllabus evidence addresses the cited knowledge expectation.",
    "Confirm whether a reviewed Malaysian occupation crosswalk "
    "and suitable demand observations are available.",
    "Review whether transferable judgement and communication skills are assessed.",
    "Confirm the intended foundational educational purpose with academic reviewers.",
    "Review whether source disagreements change the preliminary interpretation.",
]
Limitation = Literal[
    "title_only_not_taught_content",
    "needs_syllabus_confirmation",
    "no_admissible_evidence",
    "benchmark_not_teaching_evidence",
    "candidate_match_not_identity",
    "unknown_source_date",
    "stale_evidence_context_only",
    "historical_evidence",
    "broad_population_not_individual_demand",
    "exposure_not_replacement_probability",
    "model_or_study_scope_limited",
    "engineering_review_not_academic_approval",
    "rights_restrict_model_context",
    "structured_source_needs_review",
    "no_full_curriculum_completeness_claim",
    "curriculum_content_unverified",
    "disagreement_requires_review",
    "identity_bridge_unreviewed",
    "offline_synthetic",
    "live_model_not_used",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisRequest(StrictModel):
    revision_id: UUID | None = None
    idempotency_key: Key | None = None
    mode: Literal["live", "offline"] = "live"
    research: bool = True
    as_of: AwareDatetime | None = None

    @field_validator("as_of")
    @classmethod
    def historical_cutoff(cls, value: datetime | None) -> datetime | None:
        if value is not None and value > datetime.now(UTC) + timedelta(seconds=1):
            raise ValueError("Analysis cutoff cannot be in the future")
        return value


class RightsDecision(StrictModel):
    internal_analysis_allowed: bool = False
    external_model_allowed: bool = False
    excerpt_output_allowed: bool = False
    basis: str = "No explicit processing/reuse policy recorded"


class EvidenceItem(StrictModel):
    id: str
    kind: str
    record_id: UUID
    version_id: UUID
    evidence_reference_id: UUID
    source_id: UUID
    dataset_key: str | None = None
    evidence_class: str
    scope: Scope
    source_url: str | None = None
    publisher: str
    title: str
    locator: str
    excerpt: str = ""
    publication_date: str | None = None
    date_precision: Literal["day", "month", "year", "unknown"] = "unknown"
    observation_start: str | None = None
    observation_end: str | None = None
    study_period: str | None = None
    model_version: str | None = None
    language: str | None = None
    retrieved_at: AwareDatetime | None = None
    review_status: str
    is_synthetic: bool
    rights: RightsDecision
    internal_eligible: bool = False
    model_eligible: bool = False
    relevance_basis: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    exclusion_reasons: list[str] = Field(default_factory=list)
    historical_context_only: bool = False
    identity_reviewed: bool = False
    # Values are admitted structured facts only, never the original document/metadata blob.
    facts: dict[str, Any] = Field(default_factory=dict)


class CourseEvidence(StrictModel):
    id: UUID
    name: str
    year: int | None = None
    course_type: str
    evidence_level: EvidenceLevel
    is_verified: bool
    needs_syllabus_confirmation: bool
    source_url: str | None = None
    source_locator: str | None = None
    source_id: UUID | None = None
    reference_ids: list[str] = Field(default_factory=list)
    matching_terms: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class EvidencePacket(StrictModel):
    programme_id: UUID
    programme_revision_id: UUID
    institution_id: UUID
    programme_name: str
    discipline: str
    is_synthetic: bool
    as_of: AwareDatetime
    policy_version: str = POLICY_VERSION
    courses: list[CourseEvidence]
    references: list[EvidenceItem] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    radar: list[dict[str, Any]] = Field(default_factory=list)
    truncated: bool = False
    source_policy_hash: str
    manifest_hash: str = ""
    limitations: list[str] = Field(default_factory=list)


class Citation(StrictModel):
    reference_id: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=1, max_length=1500)
    scope: Scope


class DimensionFinding(StrictModel):
    status: Literal["insufficient_evidence", "investigate", "monitor"]
    citations: list[Citation] = Field(default_factory=list, max_length=10)
    review_questions: list[ReviewQuestion] = Field(default_factory=list, max_length=5)
    limitations: list[Limitation] = Field(default_factory=list, max_length=20)


class CourseFindingResult(StrictModel):
    course_id: UUID
    course_name: str
    evidence_level: EvidenceLevel
    needs_syllabus_confirmation: bool
    is_final_curriculum_verdict: Literal[False] = False
    review_flag: Literal[
        "insufficient_evidence", "investigate", "monitor", "needs_syllabus_confirmation"
    ]
    foundational_relevance: DimensionFinding
    ai_transformation: DimensionFinding
    workforce_alignment: DimensionFinding
    curriculum_currency: DimensionFinding
    future_resilience: DimensionFinding


class ProgrammeSummary(StrictModel):
    inventory_count: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    review_required_count: int = Field(ge=0)
    insufficient_evidence_count: int = Field(ge=0)
    notice: Literal[
        "Preliminary evidence-bounded screening for human academic review; "
        "no complete-curriculum or teaching-content assurance."
    ] = (
        "Preliminary evidence-bounded screening for human academic review; "
        "no complete-curriculum or teaching-content assurance."
    )


class ProgrammeInsights(StrictModel):
    verified_curriculum_evidence: list[Citation] = Field(default_factory=list)
    ai_task_developments: list[Citation] = Field(default_factory=list)
    potential_coverage_questions: list[ReviewQuestion] = Field(default_factory=list)
    review_course_ids: list[UUID] = Field(default_factory=list)
    demand_context: list[dict[str, Any]] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class ProgrammeResult(StrictModel):
    schema_version: Literal["phase4-result-1"] = SCHEMA_VERSION
    programme_revision_id: UUID
    is_synthetic: bool
    result_mode: Literal["live_model", "offline_synthetic", "deterministic_insufficiency"]
    courses: list[CourseFindingResult]
    summary: ProgrammeSummary
    insights: ProgrammeInsights = Field(default_factory=ProgrammeInsights)
