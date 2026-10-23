from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    computed_field,
    model_validator,
)

from shiftos.core.enums import CourseType, EvidenceClass, ExtractionStatus
from shiftos.schemas.common import Page

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
AcademicYear = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class CreateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InstitutionCreate(CreateModel):
    name: Name
    is_synthetic: bool = False
    website_url: HttpUrl | None = None
    source_id: UUID | None = None
    source_locator: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        | None
    ) = None


class ProgrammeInInstitutionCreate(CreateModel):
    name: Name
    programme_code: ShortText | None = None
    academic_year: AcademicYear | None = None
    version_label: ShortText = "initial"
    effective_date: date | None = None
    is_synthetic: bool = False
    level: ShortText | None = None
    discipline_key: ShortText | None = None
    canonical_url: HttpUrl | None = None
    source_id: UUID | None = None
    source_locator: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        | None
    ) = None


class ProgrammeCreate(ProgrammeInInstitutionCreate):
    institution_id: UUID


class CourseCreate(CreateModel):
    course_name: Name
    course_code: ShortText | None = None
    course_type: CourseType = CourseType.UNKNOWN
    credit_hours: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=2)
    year: int | None = Field(default=None, gt=0, le=2147483647, strict=True)
    semester: int | None = Field(default=None, gt=0, le=2147483647, strict=True)
    source_id: UUID | None = None
    source_locator: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
        | None
    ) = None
    is_verified: bool = False
    is_synthetic: bool = False

    @model_validator(mode="after")
    def verified_requires_provenance(self) -> "CourseCreate":
        if self.is_verified and (
            self.is_synthetic or not self.source_id or not self.source_locator
        ):
            raise ValueError("Verified catalogue facts require nonsynthetic source and locator")
        return self


class SourceCreate(CreateModel):
    publisher: Name
    title: Name
    url: HttpUrl | None = None
    source_kind: ShortText = "manual"
    evidence_class: EvidenceClass = EvidenceClass.INFERENCE
    license_status: ShortText = "unknown"
    published_at: AwareDatetime | None = None
    observed_at: AwareDatetime | None = None
    collected_at: AwareDatetime | None = None
    content_hash: Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9]{64}$")] | None = None
    is_synthetic: bool = False

    @model_validator(mode="after")
    def consistent_provenance(self) -> "SourceCreate":
        if self.is_synthetic != (self.evidence_class == EvidenceClass.SYNTHETIC_DEMO):
            raise ValueError("Synthetic sources must be explicitly classified synthetic_demo")
        if not self.is_synthetic and self.url is None:
            raise ValueError("Nonsynthetic sources require their origin URL")
        return self


class StoredRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_synthetic: bool


class CatalogueRecord(StoredRecord):
    source_id: UUID | None
    source_locator: str | None

    @computed_field
    @property
    def data_quality(self) -> Literal["synthetic", "source_attributed", "incomplete"]:
        if self.is_synthetic:
            return "synthetic"
        return "source_attributed" if self.source_id and self.source_locator else "incomplete"


class InstitutionRead(CatalogueRecord):
    name: str
    country: Literal["MY"]
    website_url: str | None


class ProgrammeRevisionRead(StoredRecord):
    programme_id: UUID
    version_label: str
    effective_date: date | None


class ProgrammeRead(CatalogueRecord):
    institution_id: UUID
    name: str
    programme_code: str | None
    academic_year: str | None
    active_revision_id: UUID | None
    active_revision: ProgrammeRevisionRead | None
    level: str | None
    discipline_key: str | None
    canonical_url: str | None


class CourseRead(StoredRecord):
    programme_revision_id: UUID
    course_code: str | None
    course_name: str
    course_type: CourseType
    credit_hours: Decimal | None
    year: int | None
    semester: int | None
    inventory_source_anchor_id: UUID | None
    extraction_status: ExtractionStatus
    detailed_syllabus_available: bool
    source_id: UUID | None
    source_locator: str | None
    is_verified: bool

    @computed_field
    @property
    def data_quality(
        self,
    ) -> Literal["synthetic", "source_attributed", "incomplete", "verified_catalogue"]:
        if self.is_synthetic:
            return "synthetic"
        if self.is_verified:
            return "verified_catalogue"
        return "source_attributed" if self.source_id and self.source_locator else "incomplete"


class SourceRead(StoredRecord):
    publisher: str
    title: str
    url: str | None
    source_kind: str
    evidence_class: EvidenceClass
    license_status: str
    published_at: datetime | None
    observed_at: datetime | None
    collected_at: datetime | None
    content_hash: str | None


class CoursePage(Page[CourseRead]):
    programme_revision_id: UUID | None
