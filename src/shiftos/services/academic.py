from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shiftos.core.enums import EvidenceClass
from shiftos.core.errors import DomainError
from shiftos.models import Course, Institution, Programme, ProgrammeRevision, Source
from shiftos.schemas.academic import (
    CourseCreate,
    CoursePage,
    CourseRead,
    InstitutionCreate,
    ProgrammeCreate,
    ProgrammeRead,
    ProgrammeRevisionRead,
    SourceCreate,
)


def require_institution(session: Session, institution_id: UUID) -> Institution:
    institution = session.get(Institution, institution_id)
    if institution is None:
        raise DomainError("NOT_FOUND", "Institution not found", status_code=404)
    return institution


def require_source(session: Session, source_id: UUID) -> Source:
    source = session.get(Source, source_id)
    if source is None:
        raise DomainError("NOT_FOUND", "Source not found", status_code=404)
    return source


def source_is_synthetic(session: Session, source_id: UUID | None) -> bool:
    return require_source(session, source_id).is_synthetic if source_id else False


def create_source(session: Session, data: SourceCreate) -> Source:
    values = data.model_dump()
    values["url"] = str(data.url) if data.url else None
    source = Source(**values)
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def require_programme(session: Session, programme_id: UUID) -> Programme:
    programme = session.get(Programme, programme_id)
    if programme is None:
        raise DomainError("NOT_FOUND", "Programme not found", status_code=404)
    return programme


def programme_response(session: Session, programme: Programme) -> ProgrammeRead:
    revision = (
        session.get(ProgrammeRevision, programme.active_revision_id)
        if programme.active_revision_id
        else None
    )
    return ProgrammeRead(
        id=programme.id,
        institution_id=programme.institution_id,
        name=programme.name,
        programme_code=programme.programme_code,
        academic_year=programme.academic_year,
        active_revision_id=programme.active_revision_id,
        active_revision=ProgrammeRevisionRead.model_validate(revision) if revision else None,
        is_synthetic=programme.is_synthetic,
        created_at=programme.created_at,
        updated_at=programme.updated_at,
        level=programme.level,
        discipline_key=programme.discipline_key,
        canonical_url=programme.canonical_url,
        source_id=programme.source_id,
        source_locator=programme.source_locator,
    )


def create_institution(session: Session, data: InstitutionCreate) -> Institution:
    synthetic_source = source_is_synthetic(session, data.source_id)
    values = data.model_dump()
    values["website_url"] = str(data.website_url) if data.website_url else None
    values["is_synthetic"] = data.is_synthetic or synthetic_source
    institution = Institution(**values, country="MY")
    session.add(institution)
    session.commit()
    return institution


def create_programme(session: Session, data: ProgrammeCreate) -> ProgrammeRead:
    institution = require_institution(session, data.institution_id)
    synthetic_source = source_is_synthetic(session, data.source_id)
    synthetic = data.is_synthetic or institution.is_synthetic or synthetic_source
    programme = Programme(
        institution_id=data.institution_id,
        name=data.name,
        programme_code=data.programme_code,
        academic_year=data.academic_year,
        is_synthetic=synthetic,
        level=data.level,
        discipline_key=data.discipline_key,
        canonical_url=str(data.canonical_url) if data.canonical_url else None,
        source_id=data.source_id,
        source_locator=data.source_locator,
    )
    session.add(programme)
    session.flush()
    revision = ProgrammeRevision(
        programme_id=programme.id,
        version_label=data.version_label,
        effective_date=data.effective_date,
        is_synthetic=synthetic,
    )
    session.add(revision)
    session.flush()
    programme.active_revision_id = revision.id
    session.commit()
    return programme_response(session, programme)


def create_course(session: Session, programme_id: UUID, data: CourseCreate) -> Course:
    programme = require_programme(session, programme_id)
    revision = (
        session.get(ProgrammeRevision, programme.active_revision_id)
        if programme.active_revision_id
        else None
    )
    if revision is None:
        raise DomainError("CONFLICT", "Programme has no active curriculum revision", 409)
    if revision.fixture_sha256:
        raise DomainError(
            "CONFLICT", "Imported fixture revisions are immutable; use a new revision", 409
        )
    source = require_source(session, data.source_id) if data.source_id else None
    synthetic = (
        data.is_synthetic
        or programme.is_synthetic
        or revision.is_synthetic
        or bool(source and source.is_synthetic)
    )
    if data.is_verified and (
        synthetic
        or source is None
        or source.evidence_class != EvidenceClass.VERIFIED_UNIVERSITY_FACT
    ):
        raise DomainError(
            "CONFLICT", "Verified catalogue facts require a nonsynthetic university source", 409
        )
    course = Course(
        **{**data.model_dump(), "is_synthetic": synthetic},
        programme_revision_id=revision.id,
    )
    session.add(course)
    session.commit()
    return course


def require_course(session: Session, course_id: UUID) -> Course:
    course = session.get(Course, course_id)
    if course is None:
        raise DomainError("NOT_FOUND", "Course not found", status_code=404)
    return course


def list_courses(session: Session, programme_id: UUID, limit: int, offset: int) -> CoursePage:
    programme = require_programme(session, programme_id)
    statement = select(Course).where(Course.programme_revision_id == programme.active_revision_id)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    courses = session.scalars(statement.order_by(Course.id).limit(limit).offset(offset)).all()
    return CoursePage(
        items=[CourseRead.model_validate(course) for course in courses],
        total=total,
        limit=limit,
        offset=offset,
        programme_revision_id=programme.active_revision_id,
    )
