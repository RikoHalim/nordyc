from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from shiftos.core.enums import CourseType, ExtractionStatus
from shiftos.schemas.common import Page

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
AcademicYear = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class CreateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InstitutionCreate(CreateModel):
    name: Name
    is_synthetic: bool = False


class ProgrammeCreate(CreateModel):
    institution_id: UUID
    name: Name
    programme_code: ShortText | None = None
    academic_year: AcademicYear | None = None
    version_label: ShortText = "initial"
    effective_date: date | None = None
    is_synthetic: bool = False


class StoredRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_synthetic: bool


class InstitutionRead(StoredRecord):
    name: str
    country: Literal["MY"]


class ProgrammeRevisionRead(StoredRecord):
    programme_id: UUID
    version_label: str
    effective_date: date | None


class ProgrammeRead(StoredRecord):
    institution_id: UUID
    name: str
    programme_code: str | None
    academic_year: str | None
    active_revision_id: UUID | None
    active_revision: ProgrammeRevisionRead | None


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


class CoursePage(Page[CourseRead]):
    programme_revision_id: UUID | None
