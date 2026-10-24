"""Transparent comparison contracts; calculated direction is separate from AI evidence."""

from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shiftos.schemas.academic import SourceRead
from shiftos.schemas.evidence import (
    AIImpactEvidenceRead,
    DatasetVersionRead,
    EvidenceReferenceRead,
    WorkforceObservationRead,
)

DemandClassification = Literal["RISING", "DECLINING", "STABLE", "INSUFFICIENT_DATA"]


class TrendPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method_version: Literal["workforce-radar-1"] = "workforce-radar-1"
    percent_threshold: Decimal = Field(default=Decimal("5"), ge=0, le=1000, allow_inf_nan=False)
    absolute_threshold: Decimal = Field(
        default=Decimal("0"), ge=0, le=Decimal("1000000000000000000"), allow_inf_nan=False
    )
    threshold_rule: Literal["absolute_and_percent_inclusive_nonzero"] = (
        "absolute_and_percent_inclusive_nonzero"
    )


class ObservationInput(BaseModel):
    observation: WorkforceObservationRead
    version: DatasetVersionRead
    source: SourceRead
    evidence: EvidenceReferenceRead


class AITransformationInput(BaseModel):
    evidence: AIImpactEvidenceRead
    reference: EvidenceReferenceRead
    version: DatasetVersionRead
    source: SourceRead
    match_basis: str
    supports_transformation: bool
    exclusion_reasons: list[str]


class AITransformationResult(BaseModel):
    method_version: Literal["workforce-radar-1"] = "workforce-radar-1"
    occupation_id: UUID | None
    status: Literal["AI-TRANSFORMING", "INSUFFICIENT_EVIDENCE"]
    is_ai_transforming: Literal[True] | None
    evidence: list[AITransformationInput]
    limitations: list[str]
    is_synthetic: bool
    fingerprint: str


class WorkforceTrendResult(BaseModel):
    classification: DemandClassification
    absolute_change: Decimal | None
    percentage_change: Decimal | None
    baseline_status: Literal["positive", "zero", "missing", "invalid"]
    compatible: bool
    reasons: list[str]
    population_level: str
    measurement_kind: str
    comparison_dimensions: dict[str, Any]
    period_type: str | None
    time_horizon: Literal["short_term", "two_period_comparison", "insufficient_data"]
    sustained_trend_supported: Literal[False] = False
    policy: TrendPolicy
    before: ObservationInput
    after: ObservationInput
    ai_transformation: AITransformationResult
    limitations: list[str]
    is_synthetic: bool
    fingerprint: str
