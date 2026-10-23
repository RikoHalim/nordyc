import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shiftos import cli
from shiftos.core.errors import DomainError
from shiftos.models import (
    Course,
    Document,
    DocumentAnchor,
    Institution,
    Programme,
    ProgrammeRevision,
)
from shiftos.schemas.fixtures import ProgrammeFixture
from shiftos.services.ingestion.fixtures import import_fixture


def _payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_fixture(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "programme.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_fixture_import_preserves_all_courses_facts_and_synthetic_provenance(
    session: Session, fixture_path: Path
) -> None:
    fixture = ProgrammeFixture.model_validate(_payload(fixture_path))
    result = import_fixture(session, fixture_path)
    assert result.created is True
    assert result.is_synthetic is True
    assert result.course_count == len(fixture.courses)
    assert _count(session, Course) == len(fixture.courses)
    assert _count(session, Document) == len(fixture.documents)
    expected_anchors = [anchor for course in fixture.courses for anchor in course.anchors()]
    assert _count(session, DocumentAnchor) == len(expected_anchors)
    for anchor in expected_anchors:
        stored = session.get(DocumentAnchor, anchor.id)
        assert stored.document_id == anchor.document_id
        assert stored.locator == anchor.locator
        assert stored.excerpt == anchor.excerpt
        assert stored.is_synthetic is True
    for model in (Institution, Programme, ProgrammeRevision, Course, Document, DocumentAnchor):
        assert all(record.is_synthetic for record in session.scalars(select(model)))
    programme = session.get(Programme, result.programme_id)
    assert programme.active_revision_id == result.revision_id
    structure = session.scalar(
        select(Document).where(Document.document_kind == "PROGRAMME_STRUCTURE")
    )
    assert structure.metadata_json["normalized_fixture"] == fixture.model_dump(mode="json")
    assert structure.metadata_json["disclaimer"] == fixture.disclaimer
    for course in fixture.courses:
        stored = session.get(Course, course.id)
        assert stored.inventory_source_anchor_id == course.inventory_anchor.id
        assert stored.detailed_syllabus_available == course.detailed_syllabus_available
        if not course.detailed_syllabus_available:
            assert stored.extraction_status == "INVENTORY_ONLY"
            assert not course.learning_outcomes and not course.topics and not course.assessments
        else:
            assert stored.extraction_status == "NORMALIZED_FIXTURE"
            document = session.get(Document, course.syllabus_document_id)
            persisted_ids = {fact["id"] for fact in document.metadata_json["anchored_facts"]}
            assert {str(fact.id) for _, fact in course.facts()} <= persisted_ids
    assert any(course.course_type == "ELECTIVE" for course in fixture.courses)


def test_fixture_rerun_is_idempotent_across_commits_and_file_locations(
    session: Session, fixture_path: Path, tmp_path: Path
) -> None:
    first = import_fixture(session, fixture_path)
    session.commit()
    copy = _write_fixture(tmp_path, _payload(fixture_path))
    second = import_fixture(session, copy)
    session.commit()
    assert first.programme_id == second.programme_id
    assert first.revision_id == second.revision_id
    assert second.created is False
    assert second.course_count == first.course_count
    assert _count(session, Institution) == 1
    assert _count(session, Programme) == 1
    assert _count(session, ProgrammeRevision) == 1
    assert _count(session, Course) == first.course_count


@pytest.mark.parametrize(
    "invalid",
    [
        "synthetic_false",
        "synthetic_integer",
        "document_synthetic_false",
        "orphan_inventory_anchor",
        "orphan_fact_anchor",
        "wrong_syllabus_anchor",
        "missing_syllabus_with_facts",
        "available_syllabus_without_document",
        "duplicate_course_id",
        "duplicate_anchor_id",
        "duplicate_fact_id",
        "duplicate_locator",
        "invalid_course_type",
    ],
)
def test_fixture_validation_rejects_bad_provenance_before_writing(
    session: Session, fixture_path: Path, tmp_path: Path, invalid: str
) -> None:
    payload = _payload(fixture_path)
    course = payload["courses"][0]
    fact = course["learning_outcomes"][0]
    if invalid == "synthetic_false":
        payload["is_synthetic"] = False
    elif invalid == "synthetic_integer":
        payload["is_synthetic"] = 1
    elif invalid == "document_synthetic_false":
        payload["documents"][0]["is_synthetic"] = False
    elif invalid == "orphan_inventory_anchor":
        course["inventory_anchor"]["document_id"] = str(uuid4())
    elif invalid == "orphan_fact_anchor":
        fact["document_anchor"]["document_id"] = str(uuid4())
    elif invalid == "wrong_syllabus_anchor":
        fact["document_anchor"]["document_id"] = payload["courses"][1]["syllabus_document_id"]
    elif invalid == "missing_syllabus_with_facts":
        course["detailed_syllabus_available"] = False
    elif invalid == "available_syllabus_without_document":
        course["syllabus_document_id"] = None
    elif invalid == "duplicate_course_id":
        payload["courses"][1]["id"] = course["id"]
    elif invalid == "duplicate_anchor_id":
        fact["document_anchor"]["id"] = course["inventory_anchor"]["id"]
    elif invalid == "duplicate_fact_id":
        course["learning_outcomes"][1]["id"] = fact["id"]
    elif invalid == "duplicate_locator":
        course["learning_outcomes"][1]["document_anchor"]["locator"] = fact["document_anchor"][
            "locator"
        ]
    elif invalid == "invalid_course_type":
        course["course_type"] = "ASSUMED_COMPULSORY"
    path = _write_fixture(tmp_path, payload)
    with pytest.raises(ValidationError):
        import_fixture(session, path)
    for model in (Institution, Programme, ProgrammeRevision, Course, Document, DocumentAnchor):
        assert _count(session, model) == 0


def test_fixture_changed_existing_ids_conflict_without_overwriting(
    session: Session, fixture_path: Path, tmp_path: Path
) -> None:
    first = import_fixture(session, fixture_path)
    session.commit()
    payload = _payload(fixture_path)
    course_id = UUID(payload["courses"][0]["id"])
    original_name = payload["courses"][0]["name"]
    payload["courses"][0]["name"] = "Changed course title"
    with pytest.raises(DomainError):
        import_fixture(session, _write_fixture(tmp_path, payload))
    assert session.get(Course, course_id).course_name == original_name
    assert _count(session, Course) == first.course_count
    assert not session.new
    assert not session.dirty


def test_fixture_import_does_not_commit_the_callers_transaction(
    session: Session, fixture_path: Path
) -> None:
    import_fixture(session, fixture_path)
    session.rollback()
    assert _count(session, Course) == 0
    assert _count(session, Institution) == 0


def test_cli_commits_and_prints_synthetic_result_without_credentials(
    session: Session, fixture_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    secret_url = "postgresql://private-user:private-password@example.invalid/db"
    monkeypatch.setattr(
        cli, "Settings", lambda: SimpleNamespace(database_url=SecretStr(secret_url))
    )
    monkeypatch.setattr(
        cli,
        "create_database",
        lambda _: SimpleNamespace(
            session_factory=lambda: session,
            engine=SimpleNamespace(dispose=lambda: None),
        ),
    )
    assert cli.main(["import-fixture", str(fixture_path)]) == 0
    captured = capsys.readouterr()
    response = json.loads(captured.out)
    assert response["is_synthetic"] is True
    assert response["created"] is True
    assert response["course_count"] == len(_payload(fixture_path)["courses"])
    assert "private-password" not in captured.out + captured.err
    assert session.get(Programme, UUID(response["programme_id"])) is not None
