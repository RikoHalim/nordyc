"""Deterministic observed changes with strict population and provenance boundaries."""

import calendar
import hashlib
import json
import re
from datetime import date
from decimal import localcontext
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from shiftos.core.enums import EvidenceClass
from shiftos.core.errors import DomainError
from shiftos.models import (
    AIImpactEvidence,
    DatasetVersion,
    EvidenceReference,
    Occupation,
    Source,
    WorkforceObservation,
)
from shiftos.schemas.academic import SourceRead
from shiftos.schemas.evidence import (
    AIImpactEvidenceRead,
    DatasetVersionRead,
    EvidenceReferenceRead,
    WorkforceObservationRead,
)
from shiftos.schemas.workforce_radar import (
    AITransformationInput,
    AITransformationResult,
    ObservationInput,
    TrendPolicy,
    WorkforceTrendResult,
)

DIMENSIONS = (
    "population",
    "sex",
    "age_group",
    "citizenship",
    "employment_status",
    "industry",
    "classification_version",
    "methodology",
    "sampling_frame",
    "seasonal_adjustment",
    "source_granularity",
)
OBSERVED_AI_TYPES = {"observed_capability", "observed_practice"}
PERMITTED_LEVELS = {"occupation", "occupation_group", "all_occupations"}
MEASUREMENTS = {
    "online_job_offerings": "job_advertising",
    "job_postings": "job_advertising",
    "job_offerings": "job_advertising",
    "vacancies": "vacancies",
    "employment_count": "employment",
    "employment_distribution": "employment_share",
}


def _require(session: Session, model, id: UUID):
    row = session.get(model, id)
    if row is None:
        raise DomainError("NOT_FOUND", f"{model.__name__} was not found", 404)
    return row


def _fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _observation(session: Session, id: UUID) -> ObservationInput:
    row = _require(session, WorkforceObservation, id)
    version = _require(session, DatasetVersion, row.version_id)
    return ObservationInput(
        observation=WorkforceObservationRead.model_validate(row),
        version=DatasetVersionRead.model_validate(version),
        source=SourceRead.model_validate(_require(session, Source, version.source_id)),
        evidence=EvidenceReferenceRead.model_validate(
            _require(session, EvidenceReference, row.evidence_id)
        ),
    )


def _period_type(start: date, end: date, supplied: str | None) -> str | None:
    if start.day == 1 and end.day == calendar.monthrange(end.year, end.month)[1]:
        months = (end.year - start.year) * 12 + end.month - start.month + 1
        if months == 1:
            return "month" if supplied in (None, "month", "monthly") else None
        if months == 3 and start.month in (1, 4, 7, 10):
            return "quarter" if supplied in (None, "quarter", "quarterly") else None
        if months == 12 and start.month == 1:
            return "year" if supplied in (None, "year", "annual", "yearly") else None
    if supplied == "fixed_days" and end >= start:
        return f"fixed_days:{(end - start).days + 1}"
    return None


def _dimensions(item: ObservationInput, session: Session) -> dict:
    row, version, source = item.observation, item.version, item.source
    metadata = row.metadata_json
    transform = version.metadata_json.get("transform", {})
    adapter = transform.get("adapter") if isinstance(transform, dict) else None
    level = metadata.get("population_level", "unknown")
    series = metadata.get("series_id")
    if adapter == "dosm_jmi":
        level = (
            "all_occupations" if row.occupation_label in ("Total", "Jumlah") else "occupation_group"
        )
        series = "DOSM:JMI:Summary:Table2"
    elif adapter == "employment_sector":
        level, series = "sector", "DOSM:employment_sector"
    identity = None
    if row.occupation_id:
        occupation = _require(session, Occupation, row.occupation_id)
        identity = [occupation.taxonomy, occupation.external_id, occupation.classification_code]
        if level == "unknown":
            level = "occupation"
    result = {
        "series_id": series,
        "publisher": source.publisher,
        "population_level": level,
        "occupation_identity": identity,
        "occupation_label": row.occupation_label,
        "classification_system": row.classification_system,
        "classification_code": row.classification_code,
        "sector": row.sector,
        "geography": row.geography,
        "indicator": row.indicator,
        "unit": row.unit,
        "is_synthetic": row.is_synthetic,
        "dimensions": metadata.get("dimensions", {}),
        **{key: metadata.get(key) for key in DIMENSIONS},
    }
    if adapter == "dosm_jmi":
        result["table_title"] = metadata.get("table_title")
    return result


def _empty_ai(*, is_synthetic: bool, occupation_id: UUID | None = None) -> AITransformationResult:
    result = AITransformationResult(
        occupation_id=occupation_id,
        status="INSUFFICIENT_EVIDENCE",
        is_ai_transforming=None,
        evidence=[],
        limitations=[
            "No admissible reviewed occupation-task evidence establishes transformation here. "
            "Absence of linked evidence does not establish absence of AI effects."
        ],
        is_synthetic=is_synthetic,
        fingerprint="",
    )
    result.fingerprint = _fingerprint(result.model_dump(mode="json", exclude={"fingerprint"}))
    return result


def occupation_ai_transformation(session: Session, occupation_id: UUID) -> AITransformationResult:
    occupation = _require(session, Occupation, occupation_id)
    occupation_reference = _require(session, EvidenceReference, occupation.evidence_id)
    result = _empty_ai(is_synthetic=occupation.is_synthetic, occupation_id=occupation_id)
    rows = session.scalars(
        select(AIImpactEvidence)
        .where(
            or_(
                AIImpactEvidence.occupation_id == occupation_id,
                AIImpactEvidence.occupation_label == occupation.label,
                AIImpactEvidence.metadata_json["occupation_external_id"].as_string()
                == occupation.external_id,
                (
                    AIImpactEvidence.metadata_json["classification_code"].as_string()
                    == occupation.classification_code
                )
                if occupation.classification_code
                else False,
            )
        )
        .order_by(AIImpactEvidence.id)
    ).all()
    for row in rows:
        metadata = row.metadata_json
        basis = None
        if row.occupation_id == occupation_id:
            basis = "exact_linked_occupation_id"
        elif metadata.get("occupation_match_reviewed") is True:
            if (
                metadata.get("occupation_taxonomy") not in (None, occupation.taxonomy)
                or metadata.get("occupation_external_id") not in (None, occupation.external_id)
                or metadata.get("classification_system") not in (None, occupation.taxonomy)
                or metadata.get("classification_code") not in (None, occupation.classification_code)
            ):
                continue
            if (
                metadata.get("occupation_taxonomy") == occupation.taxonomy
                and metadata.get("occupation_external_id") == occupation.external_id
            ):
                basis = "reviewed_exact_taxonomy_and_identifier"
            elif (
                occupation.classification_code
                and metadata.get("classification_system") == occupation.taxonomy
                and metadata.get("classification_code") == occupation.classification_code
            ):
                basis = "reviewed_exact_classification"
            elif row.occupation_label == occupation.label:
                # Label-only matches need an explicit reviewed identity assertion; no fuzzy aliases.
                basis = "reviewed_exact_label"
        if basis is None or row.is_synthetic != occupation.is_synthetic:
            continue
        reference = _require(session, EvidenceReference, row.evidence_id)
        version = _require(session, DatasetVersion, row.version_id)
        source = _require(session, Source, version.source_id)
        reasons = []
        if (
            reference.review_status != "reviewed"
            or occupation_reference.review_status != "reviewed"
        ):
            reasons.append("unreviewed_evidence_or_occupation_identity")
        if row.impact_type not in OBSERVED_AI_TYPES:
            reasons.append("exposure_or_prediction_does_not_establish_transformation")
        if not row.task or not row.capability:
            reasons.append("missing_documented_task_or_capability")
        if not version.publication_date or not re.match(
            r"^\d{4}(?:\b|-)", version.publication_date
        ):
            reasons.append("missing_source_date")
        expected = (
            EvidenceClass.SYNTHETIC_DEMO if row.is_synthetic else EvidenceClass.DATED_AI_CAPABILITY
        )
        if source.evidence_class != expected:
            reasons.append("inadmissible_source_evidence_class")
        if not (
            source.is_synthetic
            == version.is_synthetic
            == reference.is_synthetic
            == row.is_synthetic
        ):
            reasons.append("inconsistent_synthetic_lineage")
        if (
            metadata.get("retracted")
            or metadata.get("superseded")
            or metadata.get("correction_pending")
        ):
            reasons.append("source_correction_requires_review")
        result.evidence.append(
            AITransformationInput(
                evidence=AIImpactEvidenceRead.model_validate(row),
                reference=EvidenceReferenceRead.model_validate(reference),
                version=DatasetVersionRead.model_validate(version),
                source=SourceRead.model_validate(source),
                match_basis=basis,
                supports_transformation=not reasons,
                exclusion_reasons=reasons,
            )
        )
    if any(item.supports_transformation for item in result.evidence):
        result.status, result.is_ai_transforming = "AI-TRANSFORMING", True
        result.limitations = [
            "Documented task capability or practice changes apply to the cited study setting. "
            "They do not establish Malaysian adoption, job displacement or demand causation.",
            "Reviewed matching and interpretation are operator assertions, "
            "not independent academic approval.",
        ]
    result.fingerprint = _fingerprint(result.model_dump(mode="json", exclude={"fingerprint"}))
    return result


def compare_observations(
    session: Session,
    before_id: UUID,
    after_id: UUID,
    policy: TrendPolicy | None = None,
) -> WorkforceTrendResult:
    # Capture one consistent persisted view even when called inside an admin transaction.
    session.flush()
    policy = policy or TrendPolicy()
    before, after = _observation(session, before_id), _observation(session, after_id)
    left, right = before.observation, after.observation
    left_dimensions, right_dimensions = _dimensions(before, session), _dimensions(after, session)
    reasons = [
        f"incompatible_{key}"
        for key in left_dimensions
        if left_dimensions[key] != right_dimensions.get(key)
    ]
    if not left_dimensions["series_id"] or not right_dimensions["series_id"]:
        reasons.append("missing_series_identity")
    if any(
        not isinstance(dimensions["series_id"], (str, type(None)))
        or (isinstance(dimensions["series_id"], str) and not dimensions["series_id"].strip())
        for dimensions in (left_dimensions, right_dimensions)
    ):
        reasons.append("malformed_series_identity")
    if any(
        not isinstance(dimensions["population_level"], str)
        for dimensions in (left_dimensions, right_dimensions)
    ):
        reasons.append("malformed_population_granularity")
    if left_dimensions["population_level"] == "unknown":
        reasons.append("unknown_population_granularity")
    if not left.occupation_label and not left.sector and not left.occupation_id:
        reasons.append("missing_population_identity")
    for item in (before, after):
        observation = item.observation
        if not (
            observation.is_synthetic
            == item.version.is_synthetic
            == item.source.is_synthetic
            == item.evidence.is_synthetic
        ):
            reasons.append("inconsistent_synthetic_lineage")
        expected = (
            EvidenceClass.SYNTHETIC_DEMO
            if observation.is_synthetic
            else EvidenceClass.DATED_WORKFORCE_SIGNAL
        )
        if item.source.evidence_class != expected:
            reasons.append("inadmissible_source_evidence_class")
        if item.evidence.review_status == "rejected":
            reasons.append("rejected_source_observation")
        if observation.period_end > item.version.retrieved_at.date():
            reasons.append("observation_period_after_retrieval")
        publication_label = item.version.publication_date or ""
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", publication_label):
            try:
                publication_day = date.fromisoformat(publication_label)
            except ValueError:
                reasons.append("invalid_publication_date")
            else:
                if observation.period_end > publication_day:
                    reasons.append("observation_period_after_publication")
    left_period = _period_type(
        left.period_start, left.period_end, left.metadata_json.get("period_type")
    )
    right_period = _period_type(
        right.period_start, right.period_end, right.metadata_json.get("period_type")
    )
    if left_period is None or right_period is None or left_period != right_period:
        reasons.append("incompatible_period_types_or_durations")
    if right.period_start <= left.period_end:
        reasons.append("periods_overlap_or_are_not_chronological")
    compatible = not reasons
    measurement = MEASUREMENTS.get(left.indicator, "unknown")
    baseline_status = "positive"
    absolute, percentage = None, None
    classification = "INSUFFICIENT_DATA"
    if left.value is None or right.value is None:
        baseline_status = "missing"
        reasons.append("missing_value")
    elif (
        not left.value.is_finite()
        or not right.value.is_finite()
        or min(left.value, right.value) < 0
    ):
        baseline_status = "invalid"
        reasons.append("invalid_nonnegative_indicator_value")
    elif left.value_status != "published" or right.value_status != "published":
        baseline_status = "invalid"
        reasons.append("unpublished_or_suppressed_value")
    elif compatible:
        with localcontext() as context:
            context.prec = 50
            absolute = right.value - left.value
            if left.value == 0:
                baseline_status = "zero"
            else:
                percentage = absolute / left.value * 100
        if left_dimensions["population_level"] not in PERMITTED_LEVELS:
            reasons.append("population_does_not_support_occupational_demand")
        elif measurement not in {"job_advertising", "vacancies", "employment"}:
            reasons.append("indicator_does_not_measure_occupational_demand_or_employment")
        elif absolute == 0:
            classification = "STABLE"
        elif percentage is None:
            reasons.append("zero_baseline_percentage_change_undefined")
        elif (
            absolute.copy_abs() >= policy.absolute_threshold
            and percentage.copy_abs() >= policy.percent_threshold
        ):
            classification = "RISING" if absolute > 0 else "DECLINING"
        else:
            classification = "STABLE"
    population = str(left_dimensions["population_level"])
    horizon = "insufficient_data"
    if compatible:
        horizon = (
            "short_term"
            if left_period in {"month", "quarter"}
            and (right.period_end - left.period_start).days <= 366
            else "two_period_comparison"
        )
    ai = _empty_ai(is_synthetic=left.is_synthetic or right.is_synthetic)
    if compatible and population == "occupation" and left.occupation_id and right.occupation_id:
        ai = occupation_ai_transformation(session, right.occupation_id)
    limitations = [
        "Two observations support an observed change only; "
        "they do not establish a sustained trend or a forecast.",
        "Demand direction describes the selected published indicator and population only; "
        "occupation counts do not measure individual skills.",
        "AI evidence is evaluated independently; "
        "declining demand is never attributed to AI by this calculation.",
    ]
    if measurement == "job_advertising":
        limitations.append(
            "Job advertising is not unique vacancies, employment, hires or placements; "
            "platform coverage may change."
        )
    if measurement == "employment":
        limitations.append(
            "Employment counts describe observed employment, not job postings or unfilled demand."
        )
    if population != "occupation":
        limitations.append(
            "Broad groups, totals or sector observations cannot establish "
            "a trend for any individual occupation."
        )
    if left_period in {"month", "quarter"}:
        limitations.append(
            "Seasonality and sampling/platform changes may explain short-term fluctuations; "
            "no causal adjustment is made."
        )
    if left.evidence_id != right.evidence_id:
        limitations.extend(
            item.observation.limitations for item in (before, after) if item.observation.limitations
        )
    result = WorkforceTrendResult(
        classification=classification,
        absolute_change=absolute,
        percentage_change=percentage,
        baseline_status=baseline_status,
        compatible=compatible,
        reasons=list(dict.fromkeys(reasons)),
        population_level=population,
        measurement_kind=measurement,
        comparison_dimensions={"before": left_dimensions, "after": right_dimensions},
        period_type=left_period if left_period == right_period else None,
        time_horizon=horizon,
        policy=policy,
        before=before,
        after=after,
        ai_transformation=ai,
        limitations=limitations,
        is_synthetic=left.is_synthetic or right.is_synthetic,
        fingerprint="",
    )
    result.fingerprint = _fingerprint(result.model_dump(mode="json", exclude={"fingerprint"}))
    return result
