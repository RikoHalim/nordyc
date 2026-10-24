"""Add versioned career alignment, recommendations and append-only human review."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision: str = "0006_career_alignment"
down_revision: str | None = "0005_programme_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _record_columns():
    return [
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
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


def _json(name):
    return sa.Column(name, postgresql.JSONB(), server_default="{}", nullable=False)


def upgrade() -> None:
    op.create_table(
        "career_runs",
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
        sa.Column(
            "job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("mode", sa.String(20), nullable=False),
        _json("request_json"),
        _json("manifest_json"),
        _json("result_json"),
        _json("model_usage_json"),
        sa.Column("fingerprint", sa.String(64)),
        sa.Column("method_version", sa.String(100)),
        sa.Column("schema_version", sa.String(100)),
        sa.Column("model_name", sa.String(255)),
        *_record_columns(),
        sa.ForeignKeyConstraint(
            ["programme_revision_id", "programme_id"],
            ["programme_revisions.id", "programme_revisions.programme_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("job_id"),
        sa.UniqueConstraint("id", "programme_revision_id"),
        sa.CheckConstraint("mode IN ('live', 'offline')", name="mode"),
        sa.CheckConstraint(
            "fingerprint IS NULL OR length(fingerprint) = 64", name="fingerprint_length"
        ),
    )
    for column in ("programme_id", "programme_revision_id"):
        op.create_index(f"ix_career_runs_{column}", "career_runs", [column])
    op.create_table(
        "career_recommendations",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("programme_revision_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_key", sa.String(100), nullable=False),
        sa.Column("version_sha256", sa.String(64), nullable=False),
        _json("result_json"),
        *_record_columns(),
        sa.ForeignKeyConstraint(
            ["run_id", "programme_revision_id"],
            ["career_runs.id", "career_runs.programme_revision_id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("id", "run_id", "programme_revision_id", "version_sha256"),
        sa.UniqueConstraint("run_id", "recommendation_key"),
        sa.CheckConstraint("length(version_sha256) = 64", name="version_sha256_length"),
    )
    op.create_index("ix_career_recommendations_run_id", "career_recommendations", ["run_id"])
    op.create_table(
        "career_reviews",
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("programme_revision_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_version", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        *_record_columns(),
        sa.ForeignKeyConstraint(
            ["recommendation_id", "run_id", "programme_revision_id", "recommendation_version"],
            [
                "career_recommendations.id",
                "career_recommendations.run_id",
                "career_recommendations.programme_revision_id",
                "career_recommendations.version_sha256",
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
    )
    op.create_index("ix_career_reviews_recommendation_id", "career_reviews", ["recommendation_id"])
    # Enforce history preservation even for SQL issued outside SQLAlchemy.
    op.execute("""CREATE FUNCTION shiftos_career_append_only()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Career recommendations and reviews are append-only'; END $$""")
    for name in ("career_recommendations", "career_reviews"):
        op.execute(
            f"CREATE TRIGGER {name}_append_only BEFORE UPDATE OR DELETE ON {name} "
            "FOR EACH ROW EXECUTE FUNCTION shiftos_career_append_only()"
        )
    op.execute("""CREATE FUNCTION shiftos_career_run_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.result_json <> '{}'::jsonb THEN
            RAISE EXCEPTION 'Completed career results are immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END $$""")
    op.execute(
        "CREATE TRIGGER career_runs_immutable BEFORE UPDATE OR DELETE ON career_runs "
        "FOR EACH ROW EXECUTE FUNCTION shiftos_career_run_immutable()"
    )


def downgrade() -> None:
    query = "SELECT " + " + ".join(
        f"(SELECT count(*) FROM {name})"
        for name in ("career_reviews", "career_recommendations", "career_runs")
    )
    message = "Export Phase 5 career runs and reviews before downgrade; refusing data loss"
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
    for name in ("career_reviews", "career_recommendations", "career_runs"):
        op.drop_table(name)
    op.execute("DROP FUNCTION shiftos_career_run_immutable()")
    op.execute("DROP FUNCTION shiftos_career_append_only()")
