"""Phase 5 institutional alignment contracts; no employment probabilities."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, field_validator, model_validator

from shiftos.schemas.analysis import EvidenceItem, Key, StrictModel

METHOD_VERSION = "phase5-requirement-coverage-1"
SCHEMA_VERSION = "phase5-career-1"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
SupportType = Literal["demonstrated", "documented_intent", "possible_association", "unknown"]
GapState = Literal["supported", "partial", "documented_gap", "unknown"]


class OccupationMapping(StrictModel):
    occupation_id: UUID
    taxonomy: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    external_id: Text
    discipline: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    reviewed: bool = False
    basis: Text
    reviewer_reference: Text
    reviewed_at: AwareDatetime
    malaysia_applicability: Text
    requirements_complete: bool = False


class CompetencyAssertion(StrictModel):
    skill_id: UUID
    course_id: UUID
    anchor_id: UUID
    quote: Text
    support: SupportType
    extent: Literal["full", "partial"] = "partial"
    reviewed: bool = False
    basis: Text
    reviewer_reference: Text
    reviewed_at: AwareDatetime


class ReviewedGap(StrictModel):
    skill_id: UUID
    anchor_id: UUID
    quote: Text
    covered_course_ids: list[UUID] = Field(min_length=1, max_length=1000)
    completeness_confirmed: bool = False
    reviewed: bool = False
    basis: Text
    reviewer_reference: Text
    reviewed_at: AwareDatetime


class CareerRequest(StrictModel):
    revision_id: UUID | None = None
    idempotency_key: Key | None = None
    mode: Literal["offline", "live"] = "offline"
    as_of: AwareDatetime | None = None
    mappings: list[OccupationMapping] = Field(default_factory=list, max_length=30)
    assertions: list[CompetencyAssertion] = Field(default_factory=list, max_length=500)
    gaps: list[ReviewedGap] = Field(default_factory=list, max_length=100)

    @field_validator("as_of")
    @classmethod
    def cutoff(cls, value):
        if value is not None and value > datetime.now(UTC) + timedelta(seconds=1):
            raise ValueError("Career cutoff cannot be in the future")
        return value

    @model_validator(mode="after")
    def unique_mappings(self):
        ids = [row.occupation_id for row in self.mappings]
        if len(ids) != len(set(ids)):
            raise ValueError("Occupation mappings must be unique")
        return self


class CareerCitation(StrictModel):
    reference_id: str
    quote: Text


class CourseSupport(StrictModel):
    course_id: UUID
    support: SupportType
    extent: Literal["full", "partial"]
    citations: list[CareerCitation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RequirementFinding(StrictModel):
    occupation_id: UUID
    relationship_id: UUID
    skill_id: UUID
    skill_name: str
    requirement_type: Literal["essential", "optional", "unknown"]
    state: GapState
    support_type: SupportType = "unknown"
    courses: list[CourseSupport] = Field(default_factory=list)
    citations: list[CareerCitation] = Field(default_factory=list)
    explanation: str
    evidence_needed: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    academic_review_required: Literal[True] = True


class AlignmentMeasure(StrictModel):
    method_version: str = METHOD_VERSION
    value: float | None = Field(default=None, ge=0, le=100)
    numerator: int = Field(default=0, ge=0)
    denominator: int = Field(default=0, ge=0)
    assessed_requirements: int = Field(default=0, ge=0)
    unknown_requirements: int = Field(default=0, ge=0)
    weights: dict[str, float] = Field(default_factory=lambda: {"essential": 1.0})
    basis: str = (
        "Equal essential-requirement weights are engineering choices, not employment probability."
    )
    abstention_reason: str | None = None


class OccupationAlignment(StrictModel):
    occupation_id: UUID
    occupation_name: str
    taxonomy: str
    external_id: str
    version_id: UUID
    description: str | None = None
    mapping_basis: str
    malaysia_applicability: str
    status: Literal["supported", "partial", "insufficient_evidence"]
    requirements: list[RequirementFinding] = Field(default_factory=list)
    measure: AlignmentMeasure = Field(default_factory=AlignmentMeasure)
    rank: int | None = None
    workforce: list[dict[str, Any]] = Field(default_factory=list)
    ai_transformation: dict[str, Any] = Field(default_factory=dict)
    citations: list[CareerCitation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


ActionCategory = Literal[
    "review_learning_outcome",
    "add_practical_exercise",
    "update_assignment",
    "introduce_assessment",
    "revise_elective",
    "propose_elective",
    "industry_learning_activity",
    "applied_project",
    "request_review",
    "no_change",
]


class ActionOption(StrictModel):
    category: ActionCategory
    action: Text
    rationale: Text
    conditions: list[str] = Field(default_factory=list)


class AcademicRecommendation(StrictModel):
    key: Key
    programme_revision_id: UUID
    occupation_ids: list[UUID] = Field(default_factory=list)
    skill_id: UUID | None = None
    course_ids: list[UUID] = Field(default_factory=list)
    category: ActionCategory
    action: Text
    rationale: Text
    minimum_sufficient_intervention: Text
    alternatives: list[ActionOption] = Field(min_length=1, max_length=5)
    no_change_option: ActionOption
    competency_objective: Text
    implementation_considerations: list[str] = Field(default_factory=list)
    evidence_sufficiency: Literal["supported", "partial", "insufficient_evidence"]
    priority: Literal["review_first", "supported_need", "monitor"]
    priority_basis: Text
    citations: list[CareerCitation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    review_status: Literal["proposed", "needs_evidence"] = "proposed"
    academic_review_required: Literal[True] = True
    automatic_curriculum_change: Literal[False] = False


class CareerResult(StrictModel):
    schema_version: str = SCHEMA_VERSION
    method_version: str = METHOD_VERSION
    programme_id: UUID
    programme_revision_id: UUID
    as_of: AwareDatetime
    is_synthetic: bool
    status: Literal["supported", "partial", "insufficient_evidence"]
    occupations: list[OccupationAlignment] = Field(default_factory=list, max_length=30)
    competencies: list[RequirementFinding] = Field(default_factory=list, max_length=1000)
    recommendations: list[AcademicRecommendation] = Field(default_factory=list, max_length=100)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=300)
    course_ids: list[UUID]
    limitations: list[str] = Field(default_factory=list)
    ranking_basis: str = "Abstained: candidates do not have demonstrably comparable evidence."
    model: dict[str, Any] = Field(
        default_factory=lambda: {"status": "deterministic", "request_count": 0}
    )
    permission_policy: dict[str, Any] = Field(default_factory=dict)


class ReviewRequest(StrictModel):
    decision: Literal[
        "needs_evidence", "under_review", "approved", "rejected", "no_change_required"
    ]
    reason: Text
    expected_recommendation_version: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
