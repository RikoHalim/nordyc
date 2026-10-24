"""Versioned controlled-fixture observations, never academic accuracy estimates."""

from typing import Any, Literal

from pydantic import Field

from shiftos.schemas.analysis import StrictModel


class EvaluationCase(StrictModel):
    id: str
    dimension: str
    method: Literal["observed_output", "output_mutation", "replay_observation"]
    operation: str
    expected: Literal["accept", "reject", "abstain", "preserve"]
    description: str


class EvaluationCollection(StrictModel):
    collection_id: str
    version: str
    is_synthetic: Literal[True]
    label: str
    disciplines: dict[str, dict[str, Any]]
    cases: list[EvaluationCase] = Field(min_length=1)
    limitations: list[str]


class EvaluationObservation(StrictModel):
    case_id: str
    discipline: str
    dimension: str
    method: str
    expected: str
    observed: str
    status: Literal["pass", "fail", "not_observed"]
    error_code: str | None = None


class EvaluationMetric(StrictModel):
    dimension: str
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    not_observed: int = Field(ge=0)
    denominator: int = Field(ge=0)
    pass_rate: float | None = Field(default=None, ge=0, le=1)
    method: str = (
        "Passed executed fixture checks divided by executed checks in this dimension; "
        "not-observed checks are disclosed separately and excluded from the denominator."
    )


class EvaluationReport(StrictModel):
    schema_version: Literal["phase7-evaluation-report-1"] = "phase7-evaluation-report-1"
    method_version: Literal["phase7-controlled-invariants-1"] = "phase7-controlled-invariants-1"
    collection_id: str
    collection_version: str
    collection_sha256: str
    is_synthetic: Literal[True] = True
    academic_accuracy_claim: Literal[False] = False
    live_provider_requests: Literal[0] = 0
    database_backends: dict[str, Literal["sqlite_unit_only", "postgresql", "not_reported"]]
    implementation_methods: dict[str, dict[str, str]]
    observations: list[EvaluationObservation]
    metrics: list[EvaluationMetric]
    limitations: list[str]
