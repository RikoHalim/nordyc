"""Bounded, source-attributed catalogue manifests; never inferred syllabi."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

from shiftos.core.enums import CourseType, JobStatus
from shiftos.schemas.academic import Name, ShortText

Locator = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
Key = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ImportCourse(InputModel):
    course_name: Name
    course_code: ShortText | None = None
    year: int | None = Field(default=None, gt=0, le=100, strict=True)
    semester: int | None = Field(default=None, gt=0, le=100, strict=True)
    course_type: CourseType = CourseType.UNKNOWN
    raw_year_label: ShortText | None = None
    raw_semester_label: ShortText | None = None
    elective_group: Annotated[str, StringConstraints(max_length=255)] | None = None
    source_locator: Locator
    source_excerpt: Annotated[str, StringConstraints(min_length=1, max_length=4000)]
    review_notes: list[Note] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def title_in_excerpt(self) -> "ImportCourse":
        def normalize(text: str) -> str:
            return " ".join(text.split()).casefold()

        if normalize(self.course_name) not in normalize(self.source_excerpt):
            raise ValueError("Course title must be present in its source excerpt")
        return self


class ProgrammeManifest(InputModel):
    name: Name
    canonical_url: HttpUrl
    source_url: HttpUrl
    source_locator: Locator
    retrieved_at: AwareDatetime
    content_hash: Digest | None = None
    license_status: ShortText = "rights_unconfirmed"
    reviewed: bool = False
    notes: list[Note] = Field(default_factory=list, max_length=30)
    courses: list[ImportCourse] = Field(min_length=1, max_length=1000)

    @field_validator("retrieved_at")
    @classmethod
    def not_future(cls, value: datetime) -> datetime:
        if value > datetime.now(UTC) + timedelta(minutes=5):
            raise ValueError("Retrieval date cannot be in the future")
        return value


class CatalogueImport(InputModel):
    is_synthetic: bool = False
    idempotency_key: Key | None = None
    programmes: list[ProgrammeManifest] = Field(min_length=1, max_length=100)


class ProgrammeImport(ProgrammeManifest):
    is_synthetic: bool = False
    idempotency_key: Key | None = None


class DiscoveryRequest(InputModel):
    provider: Literal["xmum"] = "xmum"
    idempotency_key: Key | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    institution_id: UUID | None
    programme_revision_id: UUID | None
    kind: str
    status: JobStatus
    is_synthetic: bool
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    result: dict[str, Any] = Field(default_factory=dict, validation_alias="result_json")


class CoverageRead(BaseModel):
    programme_id: UUID
    programme_revision_id: UUID | None
    course_count: int
    verified_title_count: int
    needs_review_count: int
    title_only_count: int
    is_synthetic: bool
    graduation_curriculum_complete: Literal[False] = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProgrammeOutcome(BaseModel):
    programme_id: UUID | None = None
    revision_id: UUID | None = None
    name: str
    source_url: str | None = None
    status: Literal["imported", "unchanged", "historical", "failed", "discovered"]
    course_count: int = Field(default=0, ge=0)
    verified_title_count: int = Field(default=0, ge=0)
    duplicate_rows_skipped: int = Field(default=0, ge=0)
    active: bool = False
    error_code: str | None = None
    message: str | None = None


class CatalogueResult(BaseModel):
    provider: str
    directory_url: str | None = None
    directory_retrieved_at: datetime | None = None
    discovered_programmes: int = Field(default=0, ge=0)
    imported_programmes: int = Field(default=0, ge=0)
    unchanged_programmes: int = Field(default=0, ge=0)
    failed_programmes: int = Field(default=0, ge=0)
    course_count: int = Field(default=0, ge=0)
    verified_title_count: int = Field(default=0, ge=0)
    missing_from_directory: list[UUID] = Field(default_factory=list)
    entries: list[ProgrammeOutcome] = Field(default_factory=list)
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Public main-course lists are not certified complete graduation curricula",
            "Title-only information does not establish taught content; needs_syllabus_confirmation",
            "Shared MPU requirements and effective cohorts need separate confirmation",
        ]
    )
