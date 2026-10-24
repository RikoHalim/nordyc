"""Versioned institutional proposals, distinct from observations and approvals."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, field_validator, model_validator

from shiftos.schemas.analysis import EvidenceItem, Key, StrictModel
from shiftos.schemas.career import AcademicRecommendation, CareerCitation, CareerResult, Text

METHOD_VERSION = "phase6-pathways-1"
SCHEMA_VERSION = "phase6-action-plan-1"
Hours = Annotated[Decimal, Field(ge=0, le=10000, allow_inf_nan=False)]


class ResourceBinding(StrictModel):
    reference_id: UUID
    skill_id: UUID
    reviewed: bool = False
    reviewed_at: AwareDatetime
    basis: Text


class DurationBinding(StrictModel):
    recommendation_id: UUID
    step_key: Key
    hours: Hours
    component: Literal["learning", "contact", "assessment"] = "learning"
    basis_type: Literal["source", "planning_assumption"]
    reference_id: str | None = None
    quote: Text | None = None
    basis: Text
    reviewed: bool = False
    reviewed_at: AwareDatetime


class PrerequisiteBinding(StrictModel):
    target_skill_id: UUID
    prerequisite_skill_id: UUID
    reference_id: str
    quote: Text
    basis: Text
    reviewed: bool = False
    reviewed_at: AwareDatetime


class ScenarioInput(StrictModel):
    key: Literal["accelerated_ai_adoption", "gradual_workforce_transformation"]
    assumption: Literal["prioritise_assessment_review", "prioritise_incremental_coverage"]
    rationale: Text
    planning_horizon: Text | None = None
    supporting_citations: list[CareerCitation] = Field(default_factory=list, max_length=20)
    contradicting_citations: list[CareerCitation] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def consistent_assumption(self):
        expected = {
            "accelerated_ai_adoption": "prioritise_assessment_review",
            "gradual_workforce_transformation": "prioritise_incremental_coverage",
        }
        if self.assumption != expected[self.key]:
            raise ValueError("Scenario identity must match its distinct planning assumption")
        return self


class SDGMapping(StrictModel):
    recommendation_id: UUID
    sdg_reference_id: UUID
    mechanism: Literal[
        "assessed_competency_access",
        "inclusive_learning_access",
        "research_innovation",
        "resource_efficient_practice",
    ]
    rationale: Text
    citations: list[CareerCitation] = Field(min_length=1, max_length=10)
    reviewed: bool = False
    reviewed_at: AwareDatetime


class PlanRequest(StrictModel):
    idempotency_key: Key | None = None
    mode: Literal["offline", "live"] = "offline"
    as_of: AwareDatetime | None = None
    recommendation_ids: list[UUID] = Field(default_factory=list, max_length=100)
    phase4_analysis_id: UUID | None = None
    previous_plan_id: UUID | None = None
    resources: list[ResourceBinding] = Field(default_factory=list, max_length=30)
    durations: list[DurationBinding] = Field(default_factory=list, max_length=100)
    prerequisites: list[PrerequisiteBinding] = Field(default_factory=list, max_length=100)
    scenarios: list[ScenarioInput] = Field(default_factory=list, max_length=2)
    sdg_mappings: list[SDGMapping] = Field(default_factory=list, max_length=30)

    @field_validator("as_of")
    @classmethod
    def cutoff(cls, value):
        if value is not None and value > datetime.now(UTC) + timedelta(seconds=1):
            raise ValueError("Plan cutoff cannot be in the future")
        return value

    @model_validator(mode="after")
    def unique_ids(self):
        if len(self.recommendation_ids) != len(set(self.recommendation_ids)):
            raise ValueError("Recommendation identities must be unique")
        keys = [item.key for item in self.scenarios]
        if len(keys) != len(set(keys)):
            raise ValueError("Scenario identities must be distinct")
        durations = [(item.recommendation_id, item.step_key) for item in self.durations]
        if len(durations) != len(set(durations)):
            raise ValueError("A step can have only one duration basis")
        return self


class DurationEstimate(StrictModel):
    hours: Hours | None = None
    component: Literal["learning", "contact", "assessment"] = "learning"
    basis_type: Literal["source", "planning_assumption", "unknown"] = "unknown"
    basis: str = "Duration unknown; obtain a reviewed activity/workload specification."
    citations: list[CareerCitation] = Field(default_factory=list)
    reviewed_at: AwareDatetime | None = None
    guaranteed_completion_time: Literal[False] = False


class LearningResource(StrictModel):
    key: str
    reference_id: str
    skill_id: UUID
    name: str
    publisher: str
    url: str | None
    resource_type: str
    access_status: Literal["open", "restricted", "unknown"]
    cost_status: Literal["free", "paid", "unknown"]
    cost_amount: Annotated[Decimal, Field(ge=0, allow_inf_nan=False)] | None = None
    cost_currency: str | None = None
    publication_date: str | None = None
    verified_at: AwareDatetime
    verification_status: Literal["reviewed_original", "synthetic_demo"]
    licence_limitations: str
    citations: list[CareerCitation]
    limitations: list[str] = Field(default_factory=list)


class PathwayPrerequisite(StrictModel):
    skill_id: UUID
    basis: str
    citations: list[CareerCitation]
    status: Literal["source_supported", "needs_review"] = "source_supported"


class PathwayStep(StrictModel):
    key: Key
    position: int = Field(ge=1, le=100)
    purpose: Text
    objective: Text
    activity: Text
    step_type: Literal[
        "evidence_review",
        "curriculum_review",
        "proposed_practice",
        "assessment_design",
        "academic_review",
        "resource_verification",
    ]
    depends_on: list[Key] = Field(default_factory=list, max_length=20)
    ordering_basis: Literal["procedural_review", "source_prerequisite", "partially_ordered"] = (
        "procedural_review"
    )
    proposed_assessment: Text
    resource_keys: list[str] = Field(default_factory=list)
    duration: DurationEstimate = Field(default_factory=DurationEstimate)
    citations: list[CareerCitation] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    achieved_competence: Literal[False] = False


class AcademicPathway(StrictModel):
    key: Key
    programme_revision_id: UUID
    recommendation_id: UUID
    recommendation_version: str
    skill_id: UUID | None
    occupation_ids: list[UUID]
    pathway_type: Literal["academic_intervention", "evidence_review"]
    objective: Text
    steps: list[PathwayStep] = Field(min_length=1, max_length=20)
    prerequisites: list[PathwayPrerequisite] = Field(default_factory=list)
    total_hours: Hours | None = None
    known_hours: Hours = Decimal("0")
    unknown_duration_steps: int = Field(ge=0)
    duration_basis: str
    evidence_sufficiency: Literal["supported", "partial", "insufficient_evidence"]
    alternatives: list[dict[str, Any]]
    no_change_option: dict[str, Any]
    citations: list[CareerCitation]
    dependencies: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    review_status: Literal["proposed", "needs_evidence"] = "proposed"
    automatic_curriculum_change: Literal[False] = False


class RecommendationSnapshot(StrictModel):
    id: UUID
    version_sha256: str
    recommendation: AcademicRecommendation
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    consideration_status: Literal["eligible", "needs_review", "rejected", "no_change"]


class ScenarioPriority(StrictModel):
    recommendation_id: UUID
    priority: Literal["review_first", "conditional_priority", "monitor"]
    rationale: Text
    conditions: list[str] = Field(default_factory=list)


class FutureScenario(StrictModel):
    key: str
    name: str
    description: Text
    planning_horizon: str | None = None
    assumption: ScenarioInput
    occupation_ids: list[UUID]
    skill_ids: list[UUID]
    priorities: list[ScenarioPriority]
    supporting_citations: list[CareerCitation] = Field(default_factory=list)
    contradicting_citations: list[CareerCitation] = Field(default_factory=list)
    uncertainties: list[str]
    comparison_dimensions: list[str]
    is_forecast: Literal[False] = False
    probability: None = None


class ScenarioComparison(StrictModel):
    scenario_keys: list[str]
    dimensions: list[str]
    changed_recommendation_ids: list[UUID]
    unchanged_recommendation_ids: list[UUID]
    no_regret_recommendation_ids: list[UUID]
    explanation: str
    limitations: list[str] = Field(default_factory=list)


class SDGAlignment(StrictModel):
    recommendation_id: UUID
    status: Literal["possible_contribution", "insufficient_evidence", "unmapped"]
    goal_code: str | None = None
    goal_title: str | None = None
    target_code: str | None = None
    target_title: str | None = None
    mechanism: str | None = None
    rationale: str
    citations: list[CareerCitation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    measured_impact: Literal[False] = False


class ProgrammeOverview(StrictModel):
    institution_id: UUID
    institution_name: str
    programme_id: UUID
    programme_name: str
    programme_revision_id: UUID
    revision_label: str
    course_ids: list[UUID]
    phase4_context: dict[str, Any] = Field(default_factory=dict)
    evidence_coverage: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class PlanResult(StrictModel):
    schema_version: str = SCHEMA_VERSION
    method_version: str = METHOD_VERSION
    programme_id: UUID
    programme_revision_id: UUID
    career_run_id: UUID
    career_fingerprint: str
    as_of: AwareDatetime
    is_synthetic: bool
    status: Literal["supported", "partial", "insufficient_evidence"]
    overview: ProgrammeOverview
    career: CareerResult
    recommendations: list[RecommendationSnapshot]
    pathways: list[AcademicPathway] = Field(default_factory=list, max_length=100)
    resources: list[LearningResource] = Field(default_factory=list, max_length=30)
    scenarios: list[FutureScenario] = Field(min_length=2, max_length=2)
    comparison: ScenarioComparison
    sdg_alignments: list[SDGAlignment] = Field(default_factory=list, max_length=100)
    review: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=300)
    permission_policy: dict[str, Any]
    inputs: PlanRequest
    reassessment: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    model: dict[str, Any] = Field(
        default_factory=lambda: {
            "status": "deterministic",
            "request_count": 0,
            "observed_cost": None,
        }
    )


class PlanReviewRequest(StrictModel):
    decision: Literal[
        "needs_evidence", "under_review", "approved", "rejected", "no_change_required"
    ]
    reason: Text
    expected_plan_fingerprint: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
