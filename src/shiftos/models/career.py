"""Versioned career decisions reuse existing curriculum and evidence identities."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
    inspect,
)
from sqlalchemy.orm import Mapped, mapped_column

from shiftos.db.base import Base, RecordMixin, UTCDateTime
from shiftos.models.evidence import json_column
from shiftos.models.foundation import SyntheticMixin


class CareerRun(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "career_runs"
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
        Index("ix_career_runs_programme_id", "programme_id"),
        Index("ix_career_runs_programme_revision_id", "programme_revision_id"),
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
    result_json: Mapped[dict[str, Any]] = json_column()
    model_usage_json: Mapped[dict[str, Any]] = json_column()
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    method_version: Mapped[str | None] = mapped_column(String(100))
    schema_version: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(255))


class CareerRecommendation(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "career_recommendations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "programme_revision_id"],
            ["career_runs.id", "career_runs.programme_revision_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "run_id", "programme_revision_id", "version_sha256"),
        UniqueConstraint("run_id", "recommendation_key"),
        CheckConstraint("length(version_sha256) = 64", name="version_sha256_length"),
        Index("ix_career_recommendations_run_id", "run_id"),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    programme_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recommendation_key: Mapped[str] = mapped_column(String(100), nullable=False)
    version_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[dict[str, Any]] = json_column()


class CareerReview(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "career_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["recommendation_id", "run_id", "programme_revision_id", "recommendation_version"],
            [
                "career_recommendations.id",
                "career_recommendations.run_id",
                "career_recommendations.programme_revision_id",
                "career_recommendations.version_sha256",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "decision IN ('needs_evidence', 'under_review', 'approved', 'rejected', "
            "'no_change_required')",
            name="decision",
        ),
        CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),
        CheckConstraint("actor = 'authenticated_analysis_operator'", name="authenticated_actor"),
        Index("ix_career_reviews_recommendation_id", "recommendation_id"),
    )

    recommendation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    programme_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recommendation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


def _immutable(_mapper, _connection, _target):
    raise ValueError(
        "Career recommendations and reviews are append-only; create a new run or review"
    )


for _model in (CareerRecommendation, CareerReview):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _immutable)


def _immutable_result(_mapper, _connection, target):
    previous = inspect(target).attrs.result_json.history.deleted
    if (previous and previous[0]) or (not previous and target.result_json):
        raise ValueError("Completed career results are immutable; create a new run")


event.listen(CareerRun, "before_update", _immutable_result)


def _protect_completed_run(_mapper, _connection, target):
    if target.result_json:
        raise ValueError("Completed career results are immutable; create a new run")


event.listen(CareerRun, "before_delete", _protect_completed_run)
