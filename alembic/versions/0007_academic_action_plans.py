"""Add immutable academic plans, exact recommendation bindings and human reviews."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision: str = "0007_academic_action_plans"
down_revision: str | None = "0006_career_alignment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _records():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_synthetic", sa.Boolean(), server_default=sa.false(), nullable=False),
    ]


def upgrade():
    op.create_table(
        "action_plan_runs",
        sa.Column(
            "institution_id",
            sa.Uuid(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "programme_id",
            sa.Uuid(),
            sa.ForeignKey("programmes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("programme_revision_id", sa.Uuid(), nullable=False),
        sa.Column("career_run_id", sa.Uuid(), nullable=False),
        sa.Column("career_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("mode", sa.String(20), nullable=False),
        *[
            sa.Column(name, postgresql.JSONB(), server_default="{}", nullable=False)
            for name in ("request_json", "manifest_json", "result_json", "model_usage_json")
        ],
        sa.Column("fingerprint", sa.String(64)),
        sa.Column("method_version", sa.String(100)),
        sa.Column("schema_version", sa.String(100)),
        sa.Column("model_name", sa.String(255)),
        *_records(),
        sa.UniqueConstraint("job_id"),
        sa.UniqueConstraint(
            "id",
            "programme_revision_id",
            "fingerprint",
            name="uq_action_plan_runs_id_revision_fingerprint",
        ),
        sa.UniqueConstraint(
            "id",
            "career_run_id",
            "programme_revision_id",
            name="uq_action_plan_runs_id_career_revision",
        ),
        sa.ForeignKeyConstraint(
            ["career_run_id", "programme_revision_id"],
            ["career_runs.id", "career_runs.programme_revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["programme_revision_id", "programme_id"],
            ["programme_revisions.id", "programme_revisions.programme_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("mode IN ('offline', 'live')", name="mode"),
        sa.CheckConstraint("length(career_fingerprint) = 64", name="career_fingerprint_length"),
        sa.CheckConstraint(
            "fingerprint IS NULL OR length(fingerprint) = 64", name="fingerprint_length"
        ),
    )
    for column in ("career_run_id", "programme_id"):
        op.create_index(f"ix_action_plan_runs_{column}", "action_plan_runs", [column])
    op.create_table(
        "plan_recommendations",
        sa.Column("plan_run_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("career_run_id", sa.Uuid(), nullable=False),
        sa.Column("programme_revision_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_version", sa.String(64), nullable=False),
        *_records(),
        sa.UniqueConstraint("plan_run_id", "recommendation_id"),
        sa.ForeignKeyConstraint(
            ["plan_run_id", "career_run_id", "programme_revision_id"],
            [
                "action_plan_runs.id",
                "action_plan_runs.career_run_id",
                "action_plan_runs.programme_revision_id",
            ],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
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
        sa.CheckConstraint(
            "length(recommendation_version) = 64", name="recommendation_version_length"
        ),
    )
    op.create_index("ix_plan_recommendations_plan_run_id", "plan_recommendations", ["plan_run_id"])
    op.create_table(
        "action_plan_reviews",
        sa.Column("plan_run_id", sa.Uuid(), nullable=False),
        sa.Column("programme_revision_id", sa.Uuid(), nullable=False),
        sa.Column("plan_fingerprint", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        *_records(),
        sa.ForeignKeyConstraint(
            ["plan_run_id", "programme_revision_id", "plan_fingerprint"],
            [
                "action_plan_runs.id",
                "action_plan_runs.programme_revision_id",
                "action_plan_runs.fingerprint",
            ],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "decision IN ('needs_evidence', 'under_review', 'approved', 'rejected', "
            "'no_change_required')",
            name="decision",
        ),
        sa.CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),
        sa.CheckConstraint("actor = 'authenticated_analysis_operator'", name="authenticated_actor"),
        sa.CheckConstraint("length(plan_fingerprint) = 64", name="plan_fingerprint_length"),
    )
    op.create_index("ix_action_plan_reviews_plan_run_id", "action_plan_reviews", ["plan_run_id"])
    op.execute("""CREATE FUNCTION shiftos_plan_append_only()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Academic plan bindings and reviews are append-only'; END $$""")
    for table in ("plan_recommendations", "action_plan_reviews"):
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION shiftos_plan_append_only()"
        )
    op.execute("""CREATE FUNCTION shiftos_plan_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.result_json <> '{}'::jsonb THEN
            RAISE EXCEPTION 'Completed academic action plans are immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END $$""")
    op.execute(
        "CREATE TRIGGER action_plan_runs_immutable BEFORE UPDATE OR DELETE ON action_plan_runs "
        "FOR EACH ROW EXECUTE FUNCTION shiftos_plan_immutable()"
    )


def downgrade():
    tables = ("action_plan_reviews", "plan_recommendations", "action_plan_runs")
    query = "SELECT " + " + ".join(f"(SELECT count(*) FROM {table})" for table in tables)
    message = "Export Phase 6 action plans and reviews before downgrade; refusing data loss"
    if context.is_offline_mode():
        op.execute(
            "DO $$ BEGIN IF ("
            + query
            + ") > 0 THEN RAISE EXCEPTION '"
            + message
            + "'; END IF; END $$"
        )
    elif op.get_bind().scalar(sa.text(query)):
        raise RuntimeError(message)
    for table in tables:
        op.drop_table(table)
    op.execute("DROP FUNCTION shiftos_plan_immutable()")
    op.execute("DROP FUNCTION shiftos_plan_append_only()")
