from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shiftos.core.errors import DomainError
from shiftos.models import Course, Institution, Programme, ProgrammeRevision
from shiftos.schemas.academic import (
    CoursePage,
    CourseRead,
    InstitutionCreate,
    ProgrammeCreate,
    ProgrammeRead,
    ProgrammeRevisionRead,
)


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
    )


def create_institution(session: Session, data: InstitutionCreate) -> Institution:
    institution = Institution(**data.model_dump(), country="MY")
    session.add(institution)
    session.commit()
    return institution


def create_programme(session: Session, data: ProgrammeCreate) -> ProgrammeRead:
    institution = session.get(Institution, data.institution_id)
    if institution is None:
        raise DomainError("NOT_FOUND", "Institution not found", status_code=404)
    synthetic = data.is_synthetic or institution.is_synthetic
    programme = Programme(
        institution_id=data.institution_id,
        name=data.name,
        programme_code=data.programme_code,
        academic_year=data.academic_year,
        is_synthetic=synthetic,
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
