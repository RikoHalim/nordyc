"""Versioned reference evidence; these records never assert university teaching."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shiftos.db.base import Base, RecordMixin, UTCDateTime
from shiftos.models.foundation import SyntheticMixin


def json_column():
    return mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=dict, server_default="{}"
    )


class Dataset(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("registry_key"),
        CheckConstraint("length(trim(registry_key)) > 0", name="registry_key_not_blank"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
    )

    registry_key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    registry_metadata: Mapped[dict[str, Any]] = json_column()


class DatasetVersion(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "content_sha256",
            "parser_version",
            "context_sha256",
            name="uq_dataset_versions_identity",
        ),
        CheckConstraint("length(content_sha256) = 64", name="content_sha256_length"),
        CheckConstraint("length(context_sha256) = 64", name="context_sha256_length"),
        CheckConstraint("length(trim(parser_version)) > 0", name="parser_version_not_blank"),
        Index("ix_dataset_versions_dataset_id", "dataset_id"),
        Index("ix_dataset_versions_source_id", "source_id"),
    )

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
    )
    source_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    context_sha256: Mapped[str] = mapped_column(
        String(64), default="0" * 64, server_default="0" * 64, nullable=False
    )
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    publication_date: Mapped[str | None] = mapped_column(String(100))
    artifact_url: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = json_column()


class EvidenceReference(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "evidence_references"
    __table_args__ = (
        UniqueConstraint("version_id", "locator"),
        UniqueConstraint("id", "version_id"),
        CheckConstraint("length(trim(locator)) > 0", name="locator_not_blank"),
        CheckConstraint("length(trim(excerpt)) > 0", name="excerpt_not_blank"),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="positive_page_number"),
        CheckConstraint(
            "review_status IN ('needs_review', 'reviewed', 'rejected')", name="review_status"
        ),
        Index("ix_evidence_references_version_id", "version_id"),
    )

    version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False
    )
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    review_status: Mapped[str] = mapped_column(
        String(30), default="needs_review", server_default="needs_review", nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = json_column()


class ReferencedRecord:
    version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = json_column()


def record_constraints(*extra):
    return (
        UniqueConstraint("version_id", "external_id"),
        UniqueConstraint("id", "version_id"),
        CheckConstraint("length(trim(external_id)) > 0", name="external_id_not_blank"),
        ForeignKeyConstraint(
            ["evidence_id", "version_id"],
            ["evidence_references.id", "evidence_references.version_id"],
            ondelete="RESTRICT",
        ),
        *extra,
    )


def occupation_constraint():
    return ForeignKeyConstraint(
        ["occupation_id", "version_id"],
        ["occupations.id", "occupations.version_id"],
        ondelete="RESTRICT",
    )


class Occupation(RecordMixin, SyntheticMixin, ReferencedRecord, Base):
    __tablename__ = "occupations"
    __table_args__ = record_constraints(
        CheckConstraint("length(trim(label)) > 0", name="label_not_blank"),
        Index("ix_occupations_taxonomy", "taxonomy"),
    )

    taxonomy: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    classification_code: Mapped[str | None] = mapped_column(String(100))


class Skill(RecordMixin, SyntheticMixin, ReferencedRecord, Base):
    __tablename__ = "skills"
    __table_args__ = record_constraints(
        CheckConstraint("length(trim(label)) > 0", name="label_not_blank"),
        Index("ix_skills_taxonomy", "taxonomy"),
    )

    taxonomy: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class OccupationSkill(RecordMixin, SyntheticMixin, ReferencedRecord, Base):
    __tablename__ = "occupation_skills"
    __table_args__ = record_constraints(
        occupation_constraint(),
        ForeignKeyConstraint(
            ["skill_id", "version_id"], ["skills.id", "skills.version_id"], ondelete="RESTRICT"
        ),
        UniqueConstraint(
            "version_id",
            "occupation_id",
            "skill_id",
            "relationship",
            name="uq_occupation_skills_relation",
        ),
    )

    occupation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    skill_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    relationship: Mapped[str] = mapped_column(String(100), nullable=False)


class OccupationalTask(RecordMixin, SyntheticMixin, ReferencedRecord, Base):
    __tablename__ = "occupational_tasks"
    __table_args__ = record_constraints(occupation_constraint())

    occupation_id: Mapped[UUID | None] = mapped_column(Uuid)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class WorkforceObservation(RecordMixin, SyntheticMixin, ReferencedRecord, Base):
    __tablename__ = "workforce_observations"
    __table_args__ = record_constraints(
        occupation_constraint(),
        CheckConstraint("period_end >= period_start", name="valid_period"),
        CheckConstraint("length(trim(unit)) > 0", name="unit_not_blank"),
        CheckConstraint("length(trim(indicator)) > 0", name="indicator_not_blank"),
        Index("ix_workforce_observations_period_start", "period_start"),
    )

    occupation_id: Mapped[UUID | None] = mapped_column(Uuid)
    occupation_label: Mapped[str | None] = mapped_column(Text)
    classification_system: Mapped[str | None] = mapped_column(String(100))
    classification_code: Mapped[str | None] = mapped_column(String(100))
    sector: Mapped[str | None] = mapped_column(Text)
    geography: Mapped[str] = mapped_column(String(100), default="MY", server_default="MY")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    indicator: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    unit: Mapped[str] = mapped_column(String(100), nullable=False)
    value_status: Mapped[str] = mapped_column(
        String(100), default="published", server_default="published"
    )
    limitations: Mapped[str | None] = mapped_column(Text)


class AIImpactEvidence(RecordMixin, SyntheticMixin, ReferencedRecord, Base):
    __tablename__ = "ai_impact_evidence"
    __table_args__ = record_constraints(occupation_constraint())

    occupation_id: Mapped[UUID | None] = mapped_column(Uuid)
    occupation_label: Mapped[str | None] = mapped_column(Text)
    task: Mapped[str | None] = mapped_column(Text)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    impact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    capability: Mapped[str | None] = mapped_column(Text)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    study_period: Mapped[str | None] = mapped_column(String(255))


class AcademicStandard(RecordMixin, SyntheticMixin, ReferencedRecord, Base):
    __tablename__ = "academic_standards"
    __table_args__ = record_constraints()

    discipline: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    standard_code: Mapped[str | None] = mapped_column(String(100))


class SDGReference(RecordMixin, SyntheticMixin, ReferencedRecord, Base):
    __tablename__ = "sdg_references"
    __table_args__ = record_constraints(CheckConstraint("kind IN ('goal', 'target')", name="kind"))

    code: Mapped[str] = mapped_column(String(30), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    goal_code: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class EvidenceIngestionJob(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "evidence_ingestion_jobs"
    __table_args__ = (
        CheckConstraint("records_imported >= 0", name="nonnegative_records_imported"),
        CheckConstraint(
            "completed_at IS NULL OR (started_at IS NOT NULL AND completed_at >= started_at)",
            name="valid_completion_time",
        ),
        Index("ix_evidence_ingestion_jobs_dataset_id", "dataset_id"),
        Index("ix_evidence_ingestion_jobs_status", "status"),
    )

    dataset_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
    )
    version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("dataset_versions.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    records_imported: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    error: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict[str, Any]] = json_column()


class EvidenceProcessingLog(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "evidence_processing_logs"
    __table_args__ = (Index("ix_evidence_processing_logs_job_id", "job_id"),)

    job_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("evidence_ingestion_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    locator: Mapped[str | None] = mapped_column(Text)
