"""Explicit bounded change assessment; never a request to queue paid work."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from shiftos.schemas.analysis import StrictModel
from shiftos.schemas.pathways import ScenarioInput

ChangeKind = Literal[
    "programme_revision",
    "source",
    "dataset_version",
    "evidence_reference",
    "document_anchor",
    "occupation_requirement",
    "workforce_observation",
    "career_review",
    "assumption",
]


class ReplayChange(StrictModel):
    kind: ChangeKind
    id: UUID | None = None
    assumption: ScenarioInput | None = None

    @model_validator(mode="after")
    def typed_reference(self):
        if self.kind == "assumption":
            if self.id is not None or self.assumption is None:
                raise ValueError(
                    "An assumption change requires a typed scenario, not a record UUID"
                )
        elif self.id is None or self.assumption is not None:
            raise ValueError("A record change requires its exact typed UUID")
        return self


class ReplayRequest(StrictModel):
    analysis_id: UUID | None = None
    career_run_id: UUID | None = None
    plan_run_id: UUID | None = None
    changes: list[ReplayChange] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def selected_snapshot(self):
        if not any((self.analysis_id, self.career_run_id, self.plan_run_id)):
            raise ValueError("Select at least one exact existing analysis snapshot")
        keys = [
            (row.kind, row.id, row.assumption.key if row.assumption else None)
            for row in self.changes
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("Change references must be unique")
        return self


class ReplayEligibility(StrictModel):
    phase: Literal["phase4", "phase5", "phase6"]
    run_id: UUID
    current_eligible: bool
    reason_code: Literal["CURRENT", "REVALIDATION_REQUIRED", "NOT_COMPLETED"]


class ReplayImpact(StrictModel):
    kind: ChangeKind
    id: UUID | None
    classification: Literal[
        "new_analysis_required",
        "pathway_affected",
        "entire_plan_affected",
        "no_effect",
        "needs_applicability_review",
    ]
    eligibility_invalidated: bool = False
    affected_phases: list[Literal["phase4", "phase5", "phase6"]]
    affected_pathway_keys: list[str]
    reason_code: str


class ReplayAction(StrictModel):
    phase: Literal["phase4", "phase5", "phase6"]
    action: Literal["submit_new_analysis", "submit_new_career_assessment", "submit_new_action_plan"]
    requires_explicit_submission: Literal[True] = True
    requires_current_evidence: Literal[True] = True
    approvals_transfer: Literal[False] = False


class ReplayAssessment(StrictModel):
    programme_id: UUID
    active_revision_id: UUID | None
    eligibility: list[ReplayEligibility]
    impacts: list[ReplayImpact]
    actions: list[ReplayAction]
    jobs_created: Literal[0] = 0
    approvals_transferred: Literal[False] = False
    source_content_included: Literal[False] = False
    limitations: list[str]
