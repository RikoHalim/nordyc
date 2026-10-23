"""Import normalized synthetic records without document parsing or AI analysis."""

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from shiftos.core.errors import DomainError
from shiftos.models import (
    Course,
    Document,
    DocumentAnchor,
    Institution,
    Programme,
    ProgrammeRevision,
)
from shiftos.schemas.fixtures import ImportResult, ProgrammeFixture

PARSER_VERSION = "synthetic-fixture-v1"


def _checksum(value: dict[str, Any]) -> str:
    normalized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _conflict() -> DomainError:
    return DomainError(
        code="FIXTURE_CONFLICT",
        message="Fixture IDs have different content; use a new revision and record IDs.",
        status_code=409,
    )


def _assert_matches(instance: object, values: dict[str, Any]) -> None:
    if any(getattr(instance, field) != value for field, value in values.items()):
        raise _conflict()


def _document_metadata(fixture: ProgrammeFixture) -> dict[UUID, dict[str, Any]]:
    metadata = {
        document.id: {
            "fixture_id": fixture.fixture_id,
            "is_synthetic": True,
            "disclaimer": fixture.disclaimer,
            "document": document.model_dump(mode="json"),
            "anchored_facts": [],
        }
        for document in fixture.documents
    }
    for document in fixture.documents:
        if document.document_kind == "PROGRAMME_STRUCTURE":
            metadata[document.id]["normalized_fixture"] = fixture.model_dump(mode="json")
    for course in fixture.courses:
        metadata[course.inventory_anchor.document_id]["anchored_facts"].append(
            {
                "kind": "inventory",
                "course_id": str(course.id),
                "course_code": course.code,
                "course_name": course.name,
                "course_type": course.course_type,
                "document_anchor": course.inventory_anchor.model_dump(mode="json"),
            }
        )
        for category, fact in course.facts():
            metadata[fact.document_anchor.document_id]["anchored_facts"].append(
                {"kind": category, "course_id": str(course.id), **fact.model_dump(mode="json")}
            )
    return metadata


def import_fixture(session: Session, path: Path) -> ImportResult:
    """Validate the complete fixture, persist and flush; the caller owns commit/rollback.

    JSON source facts remain in document metadata for later ingestion phases. This
    service creates inventory records and anchors, never analysis or skill claims.
    """
    fixture = ProgrammeFixture.model_validate_json(path.read_text(encoding="utf-8-sig"))
    checksum = _checksum(fixture.model_dump(mode="json"))
    metadata = _document_metadata(fixture)
    institution_values = {
        "name": fixture.institution.name,
        "country": fixture.institution.country,
        "is_synthetic": True,
    }
    programme_values = {
        "institution_id": fixture.institution.id,
        "name": fixture.programme.name,
        "programme_code": fixture.programme.programme_code,
        "academic_year": fixture.programme.academic_year,
        "is_synthetic": True,
    }
    revision_values = {
        "programme_id": fixture.programme.id,
        "version_label": fixture.programme.academic_year,
        "fixture_id": fixture.fixture_id,
        "fixture_sha256": checksum,
        "is_synthetic": True,
    }
    courses = {
        course.id: {
            "programme_revision_id": fixture.programme.revision_id,
            "course_code": course.code,
            "course_name": course.name,
            "course_type": course.course_type,
            "credit_hours": course.credit_hours,
            "year": course.year,
            "semester": course.semester,
            "inventory_source_anchor_id": course.inventory_anchor.id,
            "detailed_syllabus_available": course.detailed_syllabus_available,
            "is_synthetic": True,
            "extraction_status": (
                "NORMALIZED_FIXTURE" if course.detailed_syllabus_available else "INVENTORY_ONLY"
            ),
        }
        for course in fixture.courses
    }
    documents = {}
    for document in fixture.documents:
        course_ids = [
            course.id for course in fixture.courses if course.syllabus_document_id == document.id
        ]
        documents[document.id] = {
            "programme_revision_id": fixture.programme.revision_id,
            "course_id": course_ids[0] if len(course_ids) == 1 else None,
            "filename": document.filename,
            "document_kind": document.document_kind,
            "format": "JSON",
            "content_sha256": _checksum(metadata[document.id]),
            "parser_version": PARSER_VERSION,
            "storage_path": str(path.resolve()),
            "content_status": document.content_status,
            "is_synthetic": True,
            "metadata_json": metadata[document.id],
        }
    anchors = {
        anchor.id: {
            "document_id": anchor.document_id,
            "locator": anchor.locator,
            "excerpt": anchor.excerpt,
            "is_synthetic": True,
        }
        for course in fixture.courses
        for anchor in course.anchors()
    }

    # Resolve conflicts before adding anything to the caller's transaction.
    with session.no_autoflush:
        institution = session.get(Institution, fixture.institution.id)
        programme = session.get(Programme, fixture.programme.id)
        revision = session.get(ProgrammeRevision, fixture.programme.revision_id)
        if institution is not None:
            _assert_matches(institution, institution_values)
        if programme is not None:
            _assert_matches(programme, programme_values)
        if revision is not None:
            _assert_matches(revision, revision_values)
        elif (
            session.scalar(
                select(ProgrammeRevision.id).where(
                    ProgrammeRevision.programme_id == fixture.programme.id,
                    ProgrammeRevision.version_label == fixture.programme.academic_year,
                )
            )
            is not None
        ):
            raise _conflict()
        for model, records in ((Course, courses), (Document, documents), (DocumentAnchor, anchors)):
            for identifier, values in records.items():
                existing = session.get(model, identifier)
                if existing is not None:
                    if revision is None:
                        raise _conflict()
                    comparable = {
                        key: value for key, value in values.items() if key != "storage_path"
                    }
                    _assert_matches(existing, comparable)
                elif revision is not None:
                    raise _conflict()
        if revision is not None:
            existing_ids = set(
                session.scalars(
                    select(Course.id).where(Course.programme_revision_id == revision.id)
                )
            )
            if existing_ids != set(courses):
                raise _conflict()
            return ImportResult(
                programme_id=fixture.programme.id,
                revision_id=revision.id,
                course_count=len(courses),
                created=False,
            )

    if institution is None:
        session.add(Institution(id=fixture.institution.id, **institution_values))
        session.flush()
    if programme is None:
        programme = Programme(id=fixture.programme.id, **programme_values)
        session.add(programme)
        session.flush()
    session.add(ProgrammeRevision(id=fixture.programme.revision_id, **revision_values))
    session.flush()
    stored_courses = {}
    for identifier, values in courses.items():
        course = Course(id=identifier, **{**values, "inventory_source_anchor_id": None})
        stored_courses[identifier] = course
        session.add(course)
    session.flush()
    session.add_all(Document(id=identifier, **values) for identifier, values in documents.items())
    session.flush()
    session.add_all(
        DocumentAnchor(id=identifier, **values) for identifier, values in anchors.items()
    )
    session.flush()
    for identifier, course in stored_courses.items():
        course.inventory_source_anchor_id = courses[identifier]["inventory_source_anchor_id"]
    programme.active_revision_id = fixture.programme.revision_id
    session.flush()
    return ImportResult(
        programme_id=fixture.programme.id,
        revision_id=fixture.programme.revision_id,
        course_count=len(courses),
        created=True,
    )
