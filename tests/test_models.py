import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from shiftos.core.enums import CourseType, EvidenceClass, ExtractionStatus
from shiftos.models import (
    Course,
    Document,
    DocumentAnchor,
    Institution,
    Job,
    Programme,
    ProgrammeRevision,
    Source,
)
from shiftos.services.ingestion.fixtures import import_fixture


@pytest.fixture
def synthetic_records(session: Session, fixture_path: Path) -> dict:
    import_fixture(session, fixture_path)
    session.commit()
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_default_identity_and_timestamps_use_uuid_and_utc(session: Session) -> None:
    institution = Institution(name="Synthetic Timestamp University", is_synthetic=True)
    session.add(institution)
    session.commit()
    session.refresh(institution)
    assert isinstance(institution.id, UUID)
    assert institution.country == "MY"
    assert institution.created_at.utcoffset() == timedelta(0)
    assert institution.updated_at.utcoffset() == timedelta(0)
    original_updated_at = institution.updated_at
    institution.name = "Synthetic Renamed University"
    session.commit()
    session.refresh(institution)
    assert institution.updated_at >= original_updated_at


def test_naive_timestamp_is_rejected(session: Session) -> None:
    with pytest.raises(StatementError), session.begin_nested():
        session.add(Institution(name="Synthetic Naive Timestamp", created_at=datetime(2026, 1, 1)))
        session.flush()


@pytest.mark.parametrize("values", [{"country": "US"}, {"name": " "}])
def test_institution_checks_apply_outside_api(session: Session, values: dict) -> None:
    values = {"name": "Synthetic Check University", **values}
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(Institution(**values))
        session.flush()


def test_programme_requires_existing_institution(session: Session) -> None:
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(Programme(institution_id=uuid4(), name="Synthetic Orphan Programme"))
        session.flush()


def test_revision_labels_are_unique_within_programme(
    session: Session, synthetic_records: dict
) -> None:
    revision = session.get(ProgrammeRevision, UUID(synthetic_records["programme"]["revision_id"]))
    assert revision is not None
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            ProgrammeRevision(
                programme_id=revision.programme_id, version_label=revision.version_label
            )
        )
        session.flush()


def test_active_revision_cannot_belong_to_another_programme(
    session: Session, synthetic_records: dict
) -> None:
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Programme(
                institution_id=UUID(synthetic_records["institution"]["id"]),
                name="Synthetic Different Programme",
                active_revision_id=UUID(synthetic_records["programme"]["revision_id"]),
            )
        )
        session.flush()


@pytest.mark.parametrize(
    "values",
    [
        {"programme_revision_id": uuid4()},
        {"inventory_source_anchor_id": uuid4()},
        {"course_type": "OBSOLETE"},
        {"course_name": " "},
        {"year": 0},
        {"semester": -1},
        {"credit_hours": -1},
        {"extraction_status": "INVENTED"},
        {"extraction_status": "NORMALIZED_FIXTURE", "detailed_syllabus_available": False},
    ],
)
def test_course_constraints_reject_invalid_metadata_and_references(
    session: Session, synthetic_records: dict, values: dict
) -> None:
    course_values = {
        "programme_revision_id": UUID(synthetic_records["programme"]["revision_id"]),
        "course_name": "Synthetic Constraint Course",
        **values,
    }
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(Course(**course_values))
        session.flush()


def test_duplicate_course_codes_preserve_both_inventory_entries(
    session: Session, synthetic_records: dict
) -> None:
    revision_id = UUID(synthetic_records["programme"]["revision_id"])
    duplicates = [
        Course(
            programme_revision_id=revision_id,
            course_name=f"Synthetic Ambiguous Course {number}",
            course_code="SYN-DUPLICATE",
            is_synthetic=True,
        )
        for number in range(2)
    ]
    session.add_all(duplicates)
    session.commit()
    rows = session.scalars(
        select(Course).where(
            Course.programme_revision_id == revision_id,
            Course.course_code == "SYN-DUPLICATE",
        )
    ).all()
    assert len(rows) == 2
    assert rows[0].id != rows[1].id
    assert all(row.course_type == CourseType.UNKNOWN for row in rows)
    assert all(row.extraction_status == ExtractionStatus.INVENTORY_ONLY for row in rows)
    assert all(row.detailed_syllabus_available is False for row in rows)


def test_document_cannot_attach_course_from_different_revision(
    session: Session, synthetic_records: dict
) -> None:
    revision = ProgrammeRevision(
        programme_id=UUID(synthetic_records["programme"]["id"]), version_label="second-demo"
    )
    session.add(revision)
    session.commit()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Document(
                programme_revision_id=revision.id,
                course_id=UUID(synthetic_records["courses"][0]["id"]),
                filename="synthetic_mismatch.json",
                document_kind="SYLLABUS",
                format="JSON",
                content_sha256="0" * 64,
                parser_version="synthetic-test-v1",
                is_synthetic=True,
            )
        )
        session.flush()


@pytest.mark.parametrize(
    "values",
    [
        {"document_id": uuid4()},
        {"page_number": 0},
        {"paragraph_index": -1},
        {"excerpt": " "},
        {"char_start": 0, "char_end": None},
        {"char_start": 5, "char_end": 5},
        {"char_start": -1, "char_end": 5},
    ],
)
def test_anchors_reject_invalid_sources_and_ranges(
    session: Session, synthetic_records: dict, values: dict
) -> None:
    anchor_values = {
        "document_id": UUID(synthetic_records["documents"][0]["id"]),
        "locator": "synthetic:invalid-anchor-test",
        "excerpt": "Synthetic source excerpt",
        **values,
    }
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(DocumentAnchor(**anchor_values))
        session.flush()


def test_referenced_source_document_cannot_be_deleted(
    session: Session, synthetic_records: dict
) -> None:
    document = session.get(Document, UUID(synthetic_records["documents"][0]["id"]))
    assert document is not None
    with pytest.raises(IntegrityError), session.begin_nested():
        session.delete(document)
        session.flush()


def test_job_completion_cannot_precede_start(session: Session, synthetic_records: dict) -> None:
    started_at = datetime(2026, 1, 2, tzinfo=UTC)
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Job(
                programme_revision_id=UUID(synthetic_records["programme"]["revision_id"]),
                started_at=started_at,
                completed_at=started_at - timedelta(days=1),
            )
        )
        session.flush()


@pytest.mark.parametrize("evidence_class", list(EvidenceClass))
def test_source_evidence_classes_and_unknown_dates_are_preserved(
    session: Session, evidence_class: EvidenceClass
) -> None:
    synthetic = evidence_class == EvidenceClass.SYNTHETIC_DEMO
    source = Source(
        publisher="Synthetic Test Publisher",
        title="Synthetic source metadata test",
        url=None if synthetic else "https://example.invalid/source",
        evidence_class=evidence_class,
        is_synthetic=synthetic,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    assert source.evidence_class == evidence_class
    assert source.source_kind == "manual"
    assert source.license_status == "unknown"
    assert source.published_at is None
    assert source.observed_at is None
    assert source.collected_at is None
    assert source.content_hash is None


def test_source_defaults_to_inference_and_normalizes_explicit_dates(session: Session) -> None:
    supplied_date = datetime(2026, 1, 2, tzinfo=timezone(timedelta(hours=8)))
    source = Source(
        publisher="Synthetic Test Publisher",
        title="Synthetic dated source",
        url="https://example.invalid/dated-source",
        published_at=supplied_date,
        content_hash="a" * 64,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    assert source.evidence_class == EvidenceClass.INFERENCE
    assert source.is_synthetic is False
    assert source.published_at == supplied_date
    assert source.published_at.utcoffset() == timedelta(0)
    assert source.observed_at is None
    assert source.collected_at is None


@pytest.mark.parametrize("field", ["published_at", "observed_at", "collected_at"])
def test_source_naive_dates_are_rejected(session: Session, field: str) -> None:
    with pytest.raises(StatementError), session.begin_nested():
        session.add(
            Source(
                publisher="Synthetic Test Publisher",
                title="Synthetic naive date",
                url="https://example.invalid/source",
                **{field: datetime(2026, 1, 2)},
            )
        )
        session.flush()


@pytest.mark.parametrize(
    "values",
    [
        {"publisher": " "},
        {"title": " "},
        {"url": None},
        {"url": " "},
        {"is_synthetic": True},
        {"evidence_class": EvidenceClass.SYNTHETIC_DEMO},
        {"evidence_class": "UNTRACEABLE"},
        {"content_hash": "invalid"},
    ],
)
def test_source_constraints_apply_outside_api(session: Session, values: dict) -> None:
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Source(
                **{
                    "publisher": "Synthetic Test Publisher",
                    "title": "Synthetic invalid source",
                    "url": "https://example.invalid/source",
                    **values,
                }
            )
        )
        session.flush()


@pytest.mark.parametrize("model", [Institution, Programme, Course])
def test_catalogue_source_references_cannot_be_missing(
    session: Session, synthetic_records: dict, model: type
) -> None:
    record_values = {
        Institution: {"name": "Synthetic source test institution"},
        Programme: {
            "name": "Synthetic source test programme",
            "institution_id": UUID(synthetic_records["institution"]["id"]),
        },
        Course: {
            "course_name": "Synthetic source test course",
            "programme_revision_id": UUID(synthetic_records["programme"]["revision_id"]),
        },
    }
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(model(source_id=uuid4(), **record_values[model]))
        session.flush()


@pytest.mark.parametrize("model", [Institution, Programme, Course])
def test_referenced_catalogue_source_cannot_be_deleted(
    session: Session, synthetic_records: dict, model: type
) -> None:
    source = Source(
        publisher="Synthetic Test Publisher",
        title="Synthetic retained provenance",
        evidence_class=EvidenceClass.SYNTHETIC_DEMO,
        is_synthetic=True,
    )
    session.add(source)
    session.flush()
    record_id = {
        Institution: synthetic_records["institution"]["id"],
        Programme: synthetic_records["programme"]["id"],
        Course: synthetic_records["courses"][0]["id"],
    }[model]
    record = session.get(model, UUID(record_id))
    record.source_id = source.id
    record.source_locator = "synthetic:test"
    session.commit()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.delete(source)
        session.flush()


@pytest.mark.parametrize(
    "values",
    [
        {"is_synthetic": True},
        {"source_id": None},
        {"source_locator": None},
        {"source_locator": " "},
    ],
)
def test_verified_course_requires_nonsynthetic_provenance(
    session: Session, synthetic_records: dict, values: dict
) -> None:
    source = Source(
        publisher="Synthetic Test Publisher",
        title="Synthetic provenance validation example",
        url="https://example.invalid/catalogue",
        evidence_class=EvidenceClass.VERIFIED_UNIVERSITY_FACT,
    )
    session.add(source)
    session.commit()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Course(
                **{
                    "programme_revision_id": UUID(synthetic_records["programme"]["revision_id"]),
                    "course_name": "Synthetic verification constraint test",
                    "is_verified": True,
                    "is_synthetic": False,
                    "source_id": source.id,
                    "source_locator": "#course-list",
                    **values,
                }
            )
        )
        session.flush()


def test_course_verification_only_asserts_catalogue_provenance(
    session: Session, synthetic_records: dict
) -> None:
    source = Source(
        publisher="Synthetic Test Publisher",
        title="Synthetic catalogue constraint example",
        url="https://example.invalid/catalogue",
        evidence_class=EvidenceClass.VERIFIED_UNIVERSITY_FACT,
    )
    session.add(source)
    session.flush()
    course = Course(
        programme_revision_id=UUID(synthetic_records["programme"]["revision_id"]),
        course_name="Synthetic verified catalogue entry",
        source_id=source.id,
        source_locator="#course-list",
        is_verified=True,
    )
    session.add(course)
    session.commit()
    session.refresh(course)
    assert course.is_verified is True
    assert course.detailed_syllabus_available is False
    assert course.extraction_status == ExtractionStatus.INVENTORY_ONLY
    assert course.year is None
    assert course.semester is None
    assert course.course_type == CourseType.UNKNOWN
    existing = session.get(Course, UUID(synthetic_records["courses"][0]["id"]))
    assert existing.is_verified is False
