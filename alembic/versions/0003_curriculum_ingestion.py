"""Versioned curriculum metadata and durable institution-scoped jobs.

Revision ID: 0003_curriculum_ingestion
Revises: 0002_catalogue_sources
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision: str = "0003_curriculum_ingestion"
down_revision: str | None = "0002_catalogue_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("programmes", sa.Column("ingestion_key", sa.String(64)))
    op.create_unique_constraint(
        "uq_programmes_ingestion", "programmes", ["institution_id", "ingestion_key"]
    )
    op.add_column("programme_revisions", sa.Column("import_fingerprint", sa.String(64)))
    op.add_column(
        "programme_revisions",
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_unique_constraint(
        "uq_programme_revisions_import",
        "programme_revisions",
        ["programme_id", "import_fingerprint"],
    )
    for name, kind in [
        ("raw_year_label", sa.String(100)),
        ("raw_semester_label", sa.String(100)),
        ("elective_group", sa.String(255)),
        ("source_url", sa.Text()),
    ]:
        op.add_column("courses", sa.Column(name, kind))
    op.add_column(
        "courses",
        sa.Column("review_notes", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.alter_column("jobs", "programme_revision_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("jobs", sa.Column("institution_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_jobs_institution_id_institutions",
        "jobs",
        "institutions",
        ["institution_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_jobs_institution_id", "jobs", ["institution_id"])
    op.add_column("jobs", sa.Column("idempotency_key", sa.String(100)))
    for name in ("payload_json", "result_json"):
        op.add_column(
            "jobs", sa.Column(name, postgresql.JSONB(), nullable=False, server_default="{}")
        )
    op.create_unique_constraint(
        "uq_jobs_request_key", "jobs", ["institution_id", "kind", "idempotency_key"]
    )
    op.create_check_constraint(
        op.f("ck_jobs_job_has_catalogue_target"),
        "jobs",
        "programme_revision_id IS NOT NULL OR institution_id IS NOT NULL",
    )


def downgrade() -> None:
    # Refuse to discard imported provenance/snapshots or queued/results payloads.
    query = """SELECT
      (SELECT count(*) FROM programmes WHERE ingestion_key IS NOT NULL) +
      (SELECT count(*) FROM programme_revisions WHERE import_fingerprint IS NOT NULL
        OR CAST(metadata_json AS TEXT) <> '{}') +
      (SELECT count(*) FROM courses WHERE raw_year_label IS NOT NULL
        OR raw_semester_label IS NOT NULL OR elective_group IS NOT NULL
        OR source_url IS NOT NULL OR CAST(review_notes AS TEXT) <> '[]') +
      (SELECT count(*) FROM jobs WHERE institution_id IS NOT NULL
        OR idempotency_key IS NOT NULL OR CAST(payload_json AS TEXT) <> '{}'
        OR CAST(result_json AS TEXT) <> '{}')"""
    if context.is_offline_mode():
        op.execute(
            "DO $$ BEGIN IF ("
            + query
            + ") > 0 THEN RAISE EXCEPTION 'Export Phase 2 catalogue data before downgrade';"
            " END IF; END $$"
        )
    elif op.get_bind().scalar(sa.text(query)):
        raise RuntimeError("Export Phase 2 catalogue data before downgrade; refusing data loss")
    op.drop_constraint(op.f("ck_jobs_job_has_catalogue_target"), "jobs", type_="check")
    op.drop_constraint("uq_jobs_request_key", "jobs", type_="unique")
    for name in ("result_json", "payload_json", "idempotency_key"):
        op.drop_column("jobs", name)
    op.drop_index("ix_jobs_institution_id", "jobs")
    op.drop_constraint("fk_jobs_institution_id_institutions", "jobs", type_="foreignkey")
    op.drop_column("jobs", "institution_id")
    op.alter_column("jobs", "programme_revision_id", existing_type=sa.Uuid(), nullable=False)
    for name in (
        "review_notes",
        "source_url",
        "elective_group",
        "raw_semester_label",
        "raw_year_label",
    ):
        op.drop_column("courses", name)
    op.drop_constraint("uq_programme_revisions_import", "programme_revisions", type_="unique")
    op.drop_column("programme_revisions", "metadata_json")
    op.drop_column("programme_revisions", "import_fingerprint")
    op.drop_constraint("uq_programmes_ingestion", "programmes", type_="unique")
    op.drop_column("programmes", "ingestion_key")
