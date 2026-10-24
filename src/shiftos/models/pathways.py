"""Immutable action-plan snapshots bind exact Phase 5 recommendation versions."""

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


class ActionPlanRun(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "action_plan_runs"
    __table_args__ = (
        UniqueConstraint("job_id"),
        UniqueConstraint(
            "id",
            "programme_revision_id",
            "fingerprint",
            name="uq_action_plan_runs_id_revision_fingerprint",
        ),
        UniqueConstraint(
            "id",
            "career_run_id",
            "programme_revision_id",
            name="uq_action_plan_runs_id_career_revision",
        ),
        ForeignKeyConstraint(
            ["career_run_id", "programme_revision_id"],
            ["career_runs.id", "career_runs.programme_revision_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["programme_revision_id", "programme_id"],
            ["programme_revisions.id", "programme_revisions.programme_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("mode IN ('offline', 'live')", name="mode"),
        CheckConstraint("length(career_fingerprint) = 64", name="career_fingerprint_length"),
        CheckConstraint(
            "fingerprint IS NULL OR length(fingerprint) = 64", name="fingerprint_length"
        ),
        Index("ix_action_plan_runs_career_run_id", "career_run_id"),
        Index("ix_action_plan_runs_programme_id", "programme_id"),
    )
    institution_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    programme_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False
    )
    programme_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    career_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    career_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
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


class PlanRecommendation(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "plan_recommendations"
    __table_args__ = (
        UniqueConstraint("plan_run_id", "recommendation_id"),
        ForeignKeyConstraint(
            ["plan_run_id", "career_run_id", "programme_revision_id"],
            [
                "action_plan_runs.id",
                "action_plan_runs.career_run_id",
                "action_plan_runs.programme_revision_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            [
                "recommendation_id",
                "career_run_id",
                "programme_revision_id",
                "recommendation_version",
            ],
            [
                "career_recommendations.id",
                "career_recommendations.run_id",
                "career_recommendations.programme_revision_id",
                "career_recommendations.version_sha256",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "length(recommendation_version) = 64", name="recommendation_version_length"
        ),
        Index("ix_plan_recommendations_plan_run_id", "plan_run_id"),
    )
    plan_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recommendation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    career_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    programme_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recommendation_version: Mapped[str] = mapped_column(String(64), nullable=False)


class ActionPlanReview(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "action_plan_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_run_id", "programme_revision_id", "plan_fingerprint"],
            [
                "action_plan_runs.id",
                "action_plan_runs.programme_revision_id",
                "action_plan_runs.fingerprint",
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
        CheckConstraint("length(plan_fingerprint) = 64", name="plan_fingerprint_length"),
        Index("ix_action_plan_reviews_plan_run_id", "plan_run_id"),
    )
    plan_run_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    programme_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    plan_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


def _immutable(_mapper, _connection, _target):
    raise ValueError("Action-plan recommendation bindings and reviews are append-only")


for _model in (PlanRecommendation, ActionPlanReview):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _immutable)


def _immutable_result(_mapper, _connection, target):
    previous = inspect(target).attrs.result_json.history.deleted
    if (previous and previous[0]) or (not previous and target.result_json):
        raise ValueError("Completed academic action plans are immutable; create a new run")


def _protect_completed_run(_mapper, _connection, target):
    if target.result_json:
        raise ValueError("Completed academic action plans are immutable; create a new run")


event.listen(ActionPlanRun, "before_update", _immutable_result)
event.listen(ActionPlanRun, "before_delete", _protect_completed_run)
