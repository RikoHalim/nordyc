"""Version-scoped programme analysis persistence; no academic action decisions."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from shiftos.db.base import Base, RecordMixin, UTCDateTime
from shiftos.models.evidence import json_column
from shiftos.models.foundation import SyntheticMixin


class AnalysisRun(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("job_id"),
        UniqueConstraint("id", "programme_revision_id"),
        ForeignKeyConstraint(
            ["programme_revision_id", "programme_id"],
            ["programme_revisions.id", "programme_revisions.programme_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("mode IN ('live', 'offline')", name="mode"),
        CheckConstraint(
            "fingerprint IS NULL OR length(fingerprint) = 64", name="fingerprint_length"
        ),
        Index("ix_analysis_runs_programme_id", "programme_id"),
        Index("ix_analysis_runs_institution_id", "institution_id"),
        Index("ix_analysis_runs_programme_revision_id", "programme_revision_id"),
    )

    institution_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    programme_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False
    )
    programme_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    job_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    request_json: Mapped[dict[str, Any]] = json_column()
    manifest_json: Mapped[dict[str, Any]] = json_column()
    summary_json: Mapped[dict[str, Any]] = json_column()
    research_json: Mapped[dict[str, Any]] = json_column()
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    model_name: Mapped[str | None] = mapped_column(String(255))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    schema_version: Mapped[str | None] = mapped_column(String(100))


class CourseFinding(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "course_findings"
    __table_args__ = (
        UniqueConstraint("run_id", "course_id"),
        ForeignKeyConstraint(
            ["run_id", "programme_revision_id"],
            ["analysis_runs.id", "analysis_runs.programme_revision_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id", "programme_revision_id"],
            ["courses.id", "courses.programme_revision_id"],
            ondelete="RESTRICT",
        ),
        Index("ix_course_findings_run_id", "run_id"),
        Index("ix_course_findings_course_id", "course_id"),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    programme_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    result_json: Mapped[dict[str, Any]] = json_column()


class ResearchCache(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "research_cache"
    __table_args__ = (
        UniqueConstraint("cache_key"),
        CheckConstraint("length(cache_key) = 64", name="cache_key_length"),
        CheckConstraint("length(policy_sha256) = 64", name="policy_sha256_length"),
        Index("ix_research_cache_expires_at", "expires_at"),
    )

    cache_key: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[dict[str, Any]] = json_column()
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
