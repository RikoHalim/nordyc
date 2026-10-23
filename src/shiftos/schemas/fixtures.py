"""Typed input for the explicitly synthetic, offline programme fixture."""

from collections.abc import Iterator
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

NonEmpty = Annotated[str, Field(min_length=1, max_length=1000)]


class FixtureModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*")
    @classmethod
    def reject_blank_text(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("Fixture text cannot be blank")
        return value


class SyntheticModel(FixtureModel):
    is_synthetic: Literal[True]

    @field_validator("is_synthetic", mode="before")
    @classmethod
    def require_synthetic(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Offline fixture imports require is_synthetic: true")
        return value


class FixtureInstitution(FixtureModel):
    id: UUID
    name: Annotated[str, Field(min_length=1, max_length=255)]
    country: Literal["MY"]


class FixtureProgramme(FixtureModel):
    id: UUID
    name: Annotated[str, Field(min_length=1, max_length=255)]
    academic_year: Annotated[str, Field(min_length=1, max_length=50)]
    revision_id: UUID
    programme_code: Annotated[str, Field(min_length=1, max_length=100)] | None = None


class FixtureDocument(SyntheticModel):
    id: UUID
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    document_kind: Literal["PROGRAMME_STRUCTURE", "SYLLABUS"]
    content_status: Literal["NORMALIZED_FIXTURE"]


class FixtureAnchor(FixtureModel):
    id: UUID
    document_id: UUID
    locator: Annotated[str, Field(min_length=1, max_length=500)]
    excerpt: Annotated[str, Field(min_length=1)]


class FixtureFact(FixtureModel):
    id: UUID
    text: Annotated[str, Field(min_length=1)]
    document_anchor: FixtureAnchor


class FixtureCourse(FixtureModel):
    id: UUID
    code: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    name: Annotated[str, Field(min_length=1, max_length=255)]
    course_type: Literal["COMPULSORY", "ELECTIVE", "UNKNOWN"]
    year: Annotated[int, Field(strict=True, ge=1)] | None = None
    semester: Annotated[int, Field(strict=True, ge=1)] | None = None
    credit_hours: Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=2)] | None = None
    inventory_anchor: FixtureAnchor
    detailed_syllabus_available: StrictBool
    syllabus_document_id: UUID | None
    learning_outcomes: list[FixtureFact]
    topics: list[FixtureFact]
    assessments: list[FixtureFact]

    def facts(self) -> Iterator[tuple[str, FixtureFact]]:
        for category in ("learning_outcomes", "topics", "assessments"):
            for fact in getattr(self, category):
                yield category, fact

    def anchors(self) -> Iterator[FixtureAnchor]:
        yield self.inventory_anchor
        for _, fact in self.facts():
            yield fact.document_anchor


class ProgrammeFixture(SyntheticModel):
    fixture_id: Annotated[str, Field(min_length=1, max_length=100)]
    disclaimer: NonEmpty
    institution: FixtureInstitution
    programme: FixtureProgramme
    documents: Annotated[list[FixtureDocument], Field(min_length=1)]
    courses: Annotated[list[FixtureCourse], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_identifiers_and_references(self) -> Self:
        identifiers: set[UUID] = set()
        locators: set[tuple[UUID, str]] = set()

        def register(identifier: UUID) -> None:
            if identifier in identifiers:
                raise ValueError("Fixture contains duplicate IDs")
            identifiers.add(identifier)

        register(self.institution.id)
        register(self.programme.id)
        register(self.programme.revision_id)
        documents = {document.id: document for document in self.documents}
        for document in self.documents:
            register(document.id)
        for course in self.courses:
            register(course.id)
            inventory_document = documents.get(course.inventory_anchor.document_id)
            if (
                inventory_document is None
                or inventory_document.document_kind != "PROGRAMME_STRUCTURE"
            ):
                raise ValueError(
                    "Course inventory anchor must reference a programme structure document"
                )
            if course.detailed_syllabus_available:
                syllabus = documents.get(course.syllabus_document_id)
                if syllabus is None or syllabus.document_kind != "SYLLABUS":
                    raise ValueError(
                        "Available detailed syllabus must reference a syllabus document"
                    )
            elif course.syllabus_document_id is not None or any(course.facts()):
                raise ValueError(
                    "Missing detailed syllabus cannot contain syllabus facts or a document ID"
                )
            for anchor in course.anchors():
                register(anchor.id)
                if anchor.document_id not in documents:
                    raise ValueError("Anchor references an unknown document")
                locator = (anchor.document_id, anchor.locator)
                if locator in locators:
                    raise ValueError("Fixture contains duplicate document locators")
                locators.add(locator)
            for _, fact in course.facts():
                register(fact.id)
                if fact.document_anchor.document_id != course.syllabus_document_id:
                    raise ValueError(
                        "Syllabus fact anchor must reference its course syllabus document"
                    )
        return self


class ImportResult(FixtureModel):
    programme_id: UUID
    revision_id: UUID
    course_count: int
    created: bool
    is_synthetic: Literal[True] = True
