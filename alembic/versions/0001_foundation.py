"""Create the Phase 01 academic inventory and provenance foundation.

Revision ID: 0001_foundation
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_synthetic", sa.Boolean(), server_default=sa.false(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "institutions",
        *_record_columns(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(2), server_default="MY", nullable=False),
        sa.CheckConstraint("country = 'MY'", name=op.f("ck_institutions_malaysia_only")),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_institutions_name_not_blank")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institutions")),
    )
    op.create_table(
        "programmes",
        *_record_columns(),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("programme_code", sa.String(100)),
        sa.Column("academic_year", sa.String(50)),
        sa.Column("active_revision_id", sa.Uuid()),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_programmes_name_not_blank")),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_programmes_institution_id_institutions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_programmes")),
    )
    op.create_index("ix_programmes_institution_id", "programmes", ["institution_id"])
    op.create_table(
        "programme_revisions",
        *_record_columns(),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("version_label", sa.String(100), nullable=False),
        sa.Column("effective_date", sa.Date()),
        sa.Column("fixture_id", sa.String(100)),
        sa.Column("fixture_sha256", sa.String(64)),
        sa.CheckConstraint(
            "length(trim(version_label)) > 0",
            name=op.f("ck_programme_revisions_version_label_not_blank"),
        ),
        sa.CheckConstraint(
            "fixture_sha256 IS NULL OR length(fixture_sha256) = 64",
            name=op.f("ck_programme_revisions_fixture_sha256_length"),
        ),
        sa.ForeignKeyConstraint(
            ["programme_id"],
            ["programmes.id"],
            name=op.f("fk_programme_revisions_programme_id_programmes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_programme_revisions")),
        sa.UniqueConstraint("id", "programme_id", name="uq_programme_revisions_id_programme"),
        sa.UniqueConstraint(
            "programme_id",
            "version_label",
            name=op.f("uq_programme_revisions_programme_id"),
        ),
    )
    op.create_index("ix_programme_revisions_programme_id", "programme_revisions", ["programme_id"])
    op.create_foreign_key(
        "fk_programmes_active_revision_ownership",
        "programmes",
        "programme_revisions",
        ["active_revision_id", "id"],
        ["id", "programme_id"],
    )
    op.create_table(
        "courses",
        *_record_columns(),
        sa.Column("programme_revision_id", sa.Uuid(), nullable=False),
        sa.Column("course_code", sa.String(100)),
        sa.Column("course_name", sa.String(255), nullable=False),
        sa.Column(
            "course_type",
            sa.Enum(
                "COMPULSORY",
                "ELECTIVE",
                "UNKNOWN",
                name="course_type",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="UNKNOWN",
            nullable=False,
        ),
        sa.Column("credit_hours", sa.Numeric(6, 2)),
        sa.Column("year", sa.Integer()),
        sa.Column("semester", sa.Integer()),
        sa.Column("inventory_source_anchor_id", sa.Uuid()),
        sa.Column(
            "extraction_status",
            sa.Enum(
                "INVENTORY_ONLY",
                "NORMALIZED_FIXTURE",
                "NEEDS_REVIEW",
                name="extraction_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="INVENTORY_ONLY",
            nullable=False,
        ),
        sa.Column(
            "detailed_syllabus_available",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(course_name)) > 0", name=op.f("ck_courses_name_not_blank")),
        sa.CheckConstraint("year IS NULL OR year > 0", name=op.f("ck_courses_positive_year")),
        sa.CheckConstraint(
            "semester IS NULL OR semester > 0",
            name=op.f("ck_courses_positive_semester"),
        ),
        sa.CheckConstraint(
            "credit_hours IS NULL OR credit_hours >= 0",
            name=op.f("ck_courses_nonnegative_credit_hours"),
        ),
        sa.CheckConstraint(
            "detailed_syllabus_available OR extraction_status != 'NORMALIZED_FIXTURE'",
            name=op.f("ck_courses_normalized_fixture_requires_syllabus"),
        ),
        sa.ForeignKeyConstraint(
            ["programme_revision_id"],
            ["programme_revisions.id"],
            name=op.f("fk_courses_programme_revision_id_programme_revisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("id", "programme_revision_id", name="uq_courses_id_revision"),
    )
    op.create_index(
        "ix_courses_revision_course_code",
        "courses",
        ["programme_revision_id", "course_code"],
    )
    op.create_table(
        "documents",
        *_record_columns(),
        sa.Column("programme_revision_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid()),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column(
            "document_kind",
            sa.Enum(
                "PROGRAMME_STRUCTURE",
                "SYLLABUS",
                "SUPPORTING",
                name="document_kind",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "format",
            sa.Enum(
                "PDF",
                "DOCX",
                "JSON",
                name="document_format",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.Text()),
        sa.Column(
            "content_status",
            sa.Enum(
                "UPLOADED",
                "NORMALIZED_FIXTURE",
                "NEEDS_REVIEW",
                "NEEDS_OCR",
                "FAILED",
                name="content_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="UPLOADED",
            nullable=False,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(filename)) > 0", name=op.f("ck_documents_filename_not_blank")
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name=op.f("ck_documents_content_sha256_length"),
        ),
        sa.CheckConstraint(
            "length(trim(parser_version)) > 0",
            name=op.f("ck_documents_parser_version_not_blank"),
        ),
        sa.ForeignKeyConstraint(
            ["programme_revision_id"],
            ["programme_revisions.id"],
            name=op.f("fk_documents_programme_revision_id_programme_revisions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "programme_revision_id"],
            ["courses.id", "courses.programme_revision_id"],
            name="fk_documents_course_revision",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index("ix_documents_content_sha256", "documents", ["content_sha256"])
    op.create_index(
        "ix_documents_revision_hash_parser",
        "documents",
        ["programme_revision_id", "content_sha256", "parser_version"],
    )
    op.create_table(
        "document_anchors",
        *_record_columns(),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("locator", sa.String(500), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("paragraph_index", sa.Integer()),
        sa.Column("section_label", sa.String(255)),
        sa.Column("char_start", sa.Integer()),
        sa.Column("char_end", sa.Integer()),
        sa.CheckConstraint(
            "length(trim(locator)) > 0",
            name=op.f("ck_document_anchors_locator_not_blank"),
        ),
        sa.CheckConstraint(
            "length(trim(excerpt)) > 0",
            name=op.f("ck_document_anchors_excerpt_not_blank"),
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name=op.f("ck_document_anchors_positive_page_number"),
        ),
        sa.CheckConstraint(
            "paragraph_index IS NULL OR paragraph_index >= 0",
            name=op.f("ck_document_anchors_nonnegative_paragraph_index"),
        ),
        sa.CheckConstraint(
            "(char_start IS NULL AND char_end IS NULL) OR "
            "(char_start IS NOT NULL AND char_end IS NOT NULL "
            "AND char_start >= 0 AND char_end > char_start)",
            name=op.f("ck_document_anchors_valid_character_range"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_anchors_document_id_documents"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_anchors")),
        sa.UniqueConstraint("document_id", "locator", name=op.f("uq_document_anchors_document_id")),
    )
    op.create_index("ix_document_anchors_document_id", "document_anchors", ["document_id"])
    op.create_foreign_key(
        "fk_courses_inventory_source_anchor",
        "courses",
        "document_anchors",
        ["inventory_source_anchor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "jobs",
        *_record_columns(),
        sa.Column("programme_revision_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(50), server_default="INGESTION", nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "RUNNING",
                "SUCCEEDED",
                "PARTIAL",
                "FAILED",
                name="job_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="QUEUED",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        sa.CheckConstraint("length(trim(kind)) > 0", name=op.f("ck_jobs_kind_not_blank")),
        sa.CheckConstraint(
            "completed_at IS NULL OR (started_at IS NOT NULL AND completed_at >= started_at)",
            name=op.f("ck_jobs_valid_completion_time"),
        ),
        sa.ForeignKeyConstraint(
            ["programme_revision_id"],
            ["programme_revisions.id"],
            name=op.f("fk_jobs_programme_revision_id_programme_revisions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_programme_revision_id", "jobs", ["programme_revision_id"])


def downgrade() -> None:
    op.drop_constraint("fk_courses_inventory_source_anchor", "courses", type_="foreignkey")
    op.drop_constraint("fk_programmes_active_revision_ownership", "programmes", type_="foreignkey")
    op.drop_table("jobs")
    op.drop_table("document_anchors")
    op.drop_table("documents")
    op.drop_table("courses")
    op.drop_table("programme_revisions")
    op.drop_table("programmes")
    op.drop_table("institutions")
