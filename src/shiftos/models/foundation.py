from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shiftos.core.enums import (
    ContentStatus,
    CourseType,
    DocumentFormat,
    DocumentKind,
    EvidenceClass,
    ExtractionStatus,
    JobStatus,
)
from shiftos.db.base import Base, RecordMixin, UTCDateTime, utc_now


class SyntheticMixin:
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )


class Source(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("length(trim(publisher)) > 0", name="publisher_not_blank"),
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        CheckConstraint(
            "is_synthetic = (evidence_class = 'synthetic_demo')",
            name="synthetic_evidence_consistent",
        ),
        CheckConstraint(
            "is_synthetic OR (url IS NOT NULL AND length(trim(url)) > 0)",
            name="nonsynthetic_requires_url",
        ),
        CheckConstraint(
            "content_hash IS NULL OR length(content_hash) = 64", name="content_hash_length"
        ),
    )

    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(100), default="manual", server_default="manual")
    evidence_class: Mapped[EvidenceClass] = mapped_column(
        Enum(
            EvidenceClass,
            name="evidence_class",
            values_callable=lambda members: [member.value for member in members],
            native_enum=False,
            create_constraint=True,
        ),
        default=EvidenceClass.INFERENCE,
        server_default=EvidenceClass.INFERENCE.value,
    )
    license_status: Mapped[str] = mapped_column(
        String(100), default="unknown", server_default="unknown"
    )
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    collected_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    content_hash: Mapped[str | None] = mapped_column(String(64))


class Institution(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint("country = 'MY'", name="malaysia_only"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        Index("ix_institutions_source_id", "source_id"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="MY", server_default="MY")
    website_url: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="RESTRICT")
    )
    source_locator: Mapped[str | None] = mapped_column(String(500))


class Programme(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "programmes"
    __table_args__ = (
        UniqueConstraint("institution_id", "ingestion_key", name="uq_programmes_ingestion"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        ForeignKeyConstraint(
            ["active_revision_id", "id"],
            ["programme_revisions.id", "programme_revisions.programme_id"],
            name="fk_programmes_active_revision_ownership",
            use_alter=True,
        ),
        Index("ix_programmes_institution_id", "institution_id"),
        Index("ix_programmes_source_id", "source_id"),
    )

    institution_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    programme_code: Mapped[str | None] = mapped_column(String(100))
    academic_year: Mapped[str | None] = mapped_column(String(50))
    active_revision_id: Mapped[UUID | None] = mapped_column(Uuid)
    level: Mapped[str | None] = mapped_column(String(100))
    discipline_key: Mapped[str | None] = mapped_column(String(100))
    canonical_url: Mapped[str | None] = mapped_column(Text)
    ingestion_key: Mapped[str | None] = mapped_column(String(64))
    source_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="RESTRICT")
    )
    source_locator: Mapped[str | None] = mapped_column(String(500))


class ProgrammeRevision(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "programme_revisions"
    __table_args__ = (
        UniqueConstraint("id", "programme_id", name="uq_programme_revisions_id_programme"),
        UniqueConstraint("programme_id", "version_label"),
        UniqueConstraint(
            "programme_id", "import_fingerprint", name="uq_programme_revisions_import"
        ),
        CheckConstraint("length(trim(version_label)) > 0", name="version_label_not_blank"),
        CheckConstraint(
            "fixture_sha256 IS NULL OR length(fixture_sha256) = 64",
            name="fixture_sha256_length",
        ),
        Index("ix_programme_revisions_programme_id", "programme_id"),
    )

    programme_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=False
    )
    version_label: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date)
    fixture_id: Mapped[str | None] = mapped_column(String(100))
    fixture_sha256: Mapped[str | None] = mapped_column(String(64))
    import_fingerprint: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=dict, server_default="{}"
    )


class Course(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("id", "programme_revision_id", name="uq_courses_id_revision"),
        CheckConstraint("length(trim(course_name)) > 0", name="name_not_blank"),
        CheckConstraint("year IS NULL OR year > 0", name="positive_year"),
        CheckConstraint("semester IS NULL OR semester > 0", name="positive_semester"),
        CheckConstraint(
            "credit_hours IS NULL OR credit_hours >= 0", name="nonnegative_credit_hours"
        ),
        CheckConstraint(
            "detailed_syllabus_available OR extraction_status != 'NORMALIZED_FIXTURE'",
            name="normalized_fixture_requires_syllabus",
        ),
        CheckConstraint(
            "NOT is_verified OR (NOT is_synthetic AND source_id IS NOT NULL "
            "AND source_locator IS NOT NULL AND length(trim(source_locator)) > 0)",
            name="verified_requires_provenance",
        ),
        Index("ix_courses_revision_course_code", "programme_revision_id", "course_code"),
        Index("ix_courses_source_id", "source_id"),
    )

    programme_revision_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("programme_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    course_code: Mapped[str | None] = mapped_column(String(100))
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    course_type: Mapped[CourseType] = mapped_column(
        Enum(CourseType, name="course_type", native_enum=False, create_constraint=True),
        default=CourseType.UNKNOWN,
        server_default=CourseType.UNKNOWN.value,
    )
    credit_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    year: Mapped[int | None] = mapped_column(Integer)
    semester: Mapped[int | None] = mapped_column(Integer)
    raw_year_label: Mapped[str | None] = mapped_column(String(100))
    raw_semester_label: Mapped[str | None] = mapped_column(String(100))
    elective_group: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    review_notes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=list, server_default="[]"
    )
    inventory_source_anchor_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "document_anchors.id",
            name="fk_courses_inventory_source_anchor",
            use_alter=True,
            ondelete="RESTRICT",
        ),
    )
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(
            ExtractionStatus,
            name="extraction_status",
            native_enum=False,
            create_constraint=True,
        ),
        default=ExtractionStatus.INVENTORY_ONLY,
        server_default=ExtractionStatus.INVENTORY_ONLY.value,
    )
    detailed_syllabus_available: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    source_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="RESTRICT")
    )
    source_locator: Mapped[str | None] = mapped_column(String(500))
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )


class Document(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_id", "programme_revision_id"],
            ["courses.id", "courses.programme_revision_id"],
            name="fk_documents_course_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(trim(filename)) > 0", name="filename_not_blank"),
        CheckConstraint("length(content_sha256) = 64", name="content_sha256_length"),
        CheckConstraint("length(trim(parser_version)) > 0", name="parser_version_not_blank"),
        Index("ix_documents_content_sha256", "content_sha256"),
        Index(
            "ix_documents_revision_hash_parser",
            "programme_revision_id",
            "content_sha256",
            "parser_version",
        ),
    )

    programme_revision_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("programme_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    course_id: Mapped[UUID | None] = mapped_column(Uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_kind: Mapped[DocumentKind] = mapped_column(
        Enum(
            DocumentKind,
            name="document_kind",
            native_enum=False,
            create_constraint=True,
        )
    )
    format: Mapped[DocumentFormat] = mapped_column(
        Enum(
            DocumentFormat,
            name="document_format",
            native_enum=False,
            create_constraint=True,
        )
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text)
    content_status: Mapped[ContentStatus] = mapped_column(
        Enum(
            ContentStatus,
            name="content_status",
            native_enum=False,
            create_constraint=True,
        ),
        default=ContentStatus.UPLOADED,
        server_default=ContentStatus.UPLOADED.value,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, server_default=func.now(), nullable=False
    )


class DocumentAnchor(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "document_anchors"
    __table_args__ = (
        UniqueConstraint("document_id", "locator"),
        CheckConstraint("length(trim(locator)) > 0", name="locator_not_blank"),
        CheckConstraint("length(trim(excerpt)) > 0", name="excerpt_not_blank"),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="positive_page_number"),
        CheckConstraint(
            "paragraph_index IS NULL OR paragraph_index >= 0",
            name="nonnegative_paragraph_index",
        ),
        CheckConstraint(
            "(char_start IS NULL AND char_end IS NULL) OR "
            "(char_start IS NOT NULL AND char_end IS NOT NULL "
            "AND char_start >= 0 AND char_end > char_start)",
            name="valid_character_range",
        ),
        Index("ix_document_anchors_document_id", "document_id"),
    )

    document_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    locator: Mapped[str] = mapped_column(String(500), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    paragraph_index: Mapped[int | None] = mapped_column(Integer)
    section_label: Mapped[str | None] = mapped_column(String(255))
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)


class Job(RecordMixin, SyntheticMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("institution_id", "kind", "idempotency_key", name="uq_jobs_request_key"),
        CheckConstraint(
            "programme_revision_id IS NOT NULL OR institution_id IS NOT NULL",
            name="job_has_catalogue_target",
        ),
        CheckConstraint("length(trim(kind)) > 0", name="kind_not_blank"),
        CheckConstraint(
            "completed_at IS NULL OR (started_at IS NOT NULL AND completed_at >= started_at)",
            name="valid_completion_time",
        ),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_programme_revision_id", "programme_revision_id"),
        Index("ix_jobs_institution_id", "institution_id"),
    )

    programme_revision_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("programme_revisions.id", ondelete="RESTRICT")
    )
    institution_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("institutions.id", ondelete="RESTRICT")
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=dict, server_default="{}"
    )
    result_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=dict, server_default="{}"
    )
    kind: Mapped[str] = mapped_column(String(50), default="INGESTION", server_default="INGESTION")
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False, create_constraint=True),
        default=JobStatus.QUEUED,
        server_default=JobStatus.QUEUED.value,
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    error: Mapped[str | None] = mapped_column(Text)
