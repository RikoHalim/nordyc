"""Add catalogue source attribution without changing existing academic records.

Revision ID: 0002_catalogue_sources
Revises: 0001_foundation

Downgrade is permitted only when the added fields are empty and sources has no
rows. It refuses rather than silently deleting provenance or verification data.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "0002_catalogue_sources"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("is_synthetic", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("publisher", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("source_kind", sa.String(100), server_default="manual", nullable=False),
        sa.Column(
            "evidence_class",
            sa.Enum(
                "verified_university_fact",
                "published_standard",
                "occupation_requirement",
                "dated_workforce_signal",
                "dated_ai_capability",
                "inference",
                "synthetic_demo",
                name="evidence_class",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="inference",
            nullable=False,
        ),
        sa.Column("license_status", sa.String(100), server_default="unknown", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("collected_at", sa.DateTime(timezone=True)),
        sa.Column("content_hash", sa.String(64)),
        sa.CheckConstraint(
            "length(trim(publisher)) > 0", name=op.f("ck_sources_publisher_not_blank")
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_sources_title_not_blank")),
        sa.CheckConstraint(
            "is_synthetic = (evidence_class = 'synthetic_demo')",
            name=op.f("ck_sources_synthetic_evidence_consistent"),
        ),
        sa.CheckConstraint(
            "is_synthetic OR (url IS NOT NULL AND length(trim(url)) > 0)",
            name=op.f("ck_sources_nonsynthetic_requires_url"),
        ),
        sa.CheckConstraint(
            "content_hash IS NULL OR length(content_hash) = 64",
            name=op.f("ck_sources_content_hash_length"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
    )
    op.add_column("institutions", sa.Column("website_url", sa.Text()))
    op.add_column("programmes", sa.Column("level", sa.String(100)))
    op.add_column("programmes", sa.Column("discipline_key", sa.String(100)))
    op.add_column("programmes", sa.Column("canonical_url", sa.Text()))
    for table in ("institutions", "programmes", "courses"):
        op.add_column(table, sa.Column("source_id", sa.Uuid()))
        op.add_column(table, sa.Column("source_locator", sa.String(500)))
        op.create_foreign_key(
            f"fk_{table}_source_id_sources",
            table,
            "sources",
            ["source_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_source_id", table, ["source_id"])
    op.add_column(
        "courses",
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_courses_verified_requires_provenance"),
        "courses",
        "NOT is_verified OR (NOT is_synthetic AND source_id IS NOT NULL "
        "AND source_locator IS NOT NULL AND length(trim(source_locator)) > 0)",
    )


def downgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("0002 downgrade requires a live database to check for data loss")
    connection = op.get_bind()
    # Serialize writes with the guard and subsequent DDL so provenance cannot be
    # inserted between the emptiness check and removal of the new fields.
    connection.execute(
        sa.text("LOCK TABLE sources, institutions, programmes, courses IN ACCESS EXCLUSIVE MODE")
    )
    added_metadata = {
        "sources": "TRUE",
        "institutions": "website_url IS NOT NULL OR source_id IS NOT NULL "
        "OR source_locator IS NOT NULL",
        "programmes": "level IS NOT NULL OR discipline_key IS NOT NULL "
        "OR canonical_url IS NOT NULL OR source_id IS NOT NULL OR source_locator IS NOT NULL",
        "courses": "source_id IS NOT NULL OR source_locator IS NOT NULL OR is_verified",
    }
    for table, condition in added_metadata.items():
        if connection.scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table} WHERE {condition})")):
            raise RuntimeError(
                f"Refusing 0002 downgrade: {table} contains source or catalogue metadata; "
                "preserve/export it and explicitly resolve these fields before retrying"
            )
    op.drop_constraint(op.f("ck_courses_verified_requires_provenance"), "courses", type_="check")
    op.drop_column("courses", "is_verified")
    for table in ("courses", "programmes", "institutions"):
        op.drop_index(f"ix_{table}_source_id", table_name=table)
        op.drop_constraint(f"fk_{table}_source_id_sources", table, type_="foreignkey")
        op.drop_column(table, "source_locator")
        op.drop_column(table, "source_id")
    op.drop_column("programmes", "canonical_url")
    op.drop_column("programmes", "discipline_key")
    op.drop_column("programmes", "level")
    op.drop_column("institutions", "website_url")
    op.drop_table("sources")
