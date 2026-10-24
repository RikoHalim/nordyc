"""Read contracts for reference evidence, preserving unknowns and date precision."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from shiftos.schemas.academic import SourceRead


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    is_synthetic: bool


class DatasetRead(EvidenceRead):
    registry_key: str
    name: str
    category: str
    registry_metadata: dict[str, Any]
    latest_ingestion_status: str | None = None


class DatasetVersionRead(EvidenceRead):
    dataset_id: UUID
    source_id: UUID
    content_sha256: str
    parser_version: str
    context_sha256: str
    retrieved_at: datetime
    publication_date: str | None
    artifact_url: str
    metadata_json: dict[str, Any]


class EvidenceReferenceRead(EvidenceRead):
    version_id: UUID
    locator: str
    excerpt: str
    page_number: int | None
    review_status: str
    metadata_json: dict[str, Any]


class ReferencedRead(EvidenceRead):
    version_id: UUID
    evidence_id: UUID
    external_id: str
    metadata_json: dict[str, Any]


class OccupationRead(ReferencedRead):
    taxonomy: str
    label: str
    description: str | None
    classification_code: str | None


class SkillRead(ReferencedRead):
    taxonomy: str
    label: str
    description: str | None


class OccupationSkillRead(ReferencedRead):
    occupation_id: UUID
    skill_id: UUID
    relationship: str
    skill: SkillRead


class OccupationalTaskRead(ReferencedRead):
    occupation_id: UUID | None
    description: str


class WorkforceObservationRead(ReferencedRead):
    occupation_id: UUID | None
    occupation_label: str | None
    classification_system: str | None
    classification_code: str | None
    sector: str | None
    geography: str
    period_start: date
    period_end: date
    indicator: str
    value: Decimal | None
    unit: str
    value_status: str
    limitations: str | None


class AIImpactEvidenceRead(ReferencedRead):
    occupation_id: UUID | None
    occupation_label: str | None
    task: str | None
    statement: str
    impact_type: str
    capability: str | None
    limitations: str
    study_period: str | None


class AcademicStandardRead(ReferencedRead):
    discipline: str
    title: str
    statement: str
    standard_code: str | None


class SDGReferenceRead(ReferencedRead):
    code: str
    kind: str
    goal_code: str
    title: str
    description: str


class EvidenceIngestionJobRead(EvidenceRead):
    dataset_id: UUID
    version_id: UUID | None
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    records_imported: int
    error: str | None
    result_json: dict[str, Any]


class EvidenceProcessingLogRead(EvidenceRead):
    job_id: UUID
    level: str
    code: str
    message: str
    locator: str | None


class VersionProvenance(BaseModel):
    dataset: DatasetRead
    version: DatasetVersionRead
    source: SourceRead
    record_counts: dict[str, int]


class ReferenceProvenance(VersionProvenance):
    evidence: EvidenceReferenceRead
