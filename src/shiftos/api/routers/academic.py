from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shiftos.db.session import get_session
from shiftos.models import Institution, Programme
from shiftos.schemas.academic import (
    CoursePage,
    InstitutionCreate,
    InstitutionRead,
    ProgrammeCreate,
    ProgrammeRead,
)
from shiftos.schemas.common import ErrorResponse, Page
from shiftos.services import academic

router = APIRouter(
    prefix="/api/v1",
    tags=["Academic structure"],
    responses={code: {"model": ErrorResponse} for code in (404, 409, 422, 503)},
)
SessionDependency = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.post("/institutions", response_model=InstitutionRead, status_code=201)
def create_institution(data: InstitutionCreate, session: SessionDependency) -> Institution:
    return academic.create_institution(session, data)


@router.get("/institutions", response_model=Page[InstitutionRead])
def list_institutions(session: SessionDependency, limit: Limit = 50, offset: Offset = 0) -> dict:
    institutions = session.scalars(
        select(Institution).order_by(Institution.id).limit(limit).offset(offset)
    ).all()
    return {
        "items": institutions,
        "total": session.scalar(select(func.count()).select_from(Institution)) or 0,
        "limit": limit,
        "offset": offset,
    }


@router.post("/programmes", response_model=ProgrammeRead, status_code=201)
def create_programme(data: ProgrammeCreate, session: SessionDependency) -> ProgrammeRead:
    return academic.create_programme(session, data)


@router.get("/programmes", response_model=Page[ProgrammeRead])
def list_programmes(session: SessionDependency, limit: Limit = 50, offset: Offset = 0) -> dict:
    programmes = session.scalars(
        select(Programme).order_by(Programme.id).limit(limit).offset(offset)
    ).all()
    return {
        "items": [academic.programme_response(session, programme) for programme in programmes],
        "total": session.scalar(select(func.count()).select_from(Programme)) or 0,
        "limit": limit,
        "offset": offset,
    }


@router.get("/programmes/{id}", response_model=ProgrammeRead)
def read_programme(id: UUID, session: SessionDependency) -> ProgrammeRead:
    return academic.programme_response(session, academic.require_programme(session, id))


@router.get("/programmes/{id}/courses", response_model=CoursePage)
def list_courses(
    id: UUID, session: SessionDependency, limit: Limit = 50, offset: Offset = 0
) -> CoursePage:
    return academic.list_courses(session, id, limit, offset)
