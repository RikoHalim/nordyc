"""Catalogue jobs, structured fallback and reproducible revision access."""

import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from shiftos.core.errors import DomainError
from shiftos.db.session import get_session
from shiftos.schemas.academic import CoursePage, ProgrammeRevisionRead
from shiftos.schemas.common import ErrorResponse, Page
from shiftos.schemas.ingestion import (
    CatalogueImport,
    CoverageRead,
    DiscoveryRequest,
    JobRead,
    ProgrammeImport,
)
from shiftos.services.academic import list_courses, require_programme
from shiftos.services.ingestion.catalogue import (
    coverage,
    enqueue_import,
    require_job,
    revision_list,
)
from shiftos.services.ingestion.worker import PROVIDERS, provider_institution, queue_discovery

router = APIRouter(
    prefix="/api/v1",
    tags=["Curriculum ingestion"],
    responses={code: {"model": ErrorResponse} for code in (401, 404, 409, 413, 422, 503)},
)
SessionDep = Annotated[Session, Depends(get_session)]


def require_writer(
    request: Request, x_catalogue_token: Annotated[str | None, Header()] = None
) -> None:
    settings = request.app.state.settings
    token = settings.catalogue_write_token
    if settings.app_env == "production" and token is None:
        raise DomainError(
            "CATALOGUE_WRITE_DISABLED",
            "Configure catalogue write authorization before production use",
            503,
        )
    if token is not None and not hmac.compare_digest(
        token.get_secret_value().encode(), (x_catalogue_token or "").encode()
    ):
        raise DomainError("NOT_AUTHORIZED", "Catalogue write authorization required", 401)


Writer = Annotated[None, Depends(require_writer)]


@router.get("/catalogue/providers")
def providers() -> dict:
    return {
        "items": [
            {
                "key": key,
                "name": value["name"],
                "website_url": value["website_url"],
                "directory_url": value["directory_url"],
            }
            for key, value in PROVIDERS.items()
        ]
    }


@router.post("/catalogue/discover", response_model=JobRead, status_code=202)
def discover_provider(data: DiscoveryRequest, session: SessionDep, _writer: Writer):
    institution = provider_institution(session, data.provider)
    return queue_discovery(session, institution.id, data.provider, data.idempotency_key)


@router.post("/institutions/{id}/discover", response_model=JobRead, status_code=202)
def discover(id: UUID, data: DiscoveryRequest, session: SessionDep, _writer: Writer):
    return queue_discovery(session, id, data.provider, data.idempotency_key)


@router.post("/institutions/{id}/imports", response_model=JobRead, status_code=202)
def import_institution(id: UUID, data: CatalogueImport, session: SessionDep, _writer: Writer):
    return enqueue_import(session, id, data)


@router.post("/programmes/{id}/imports", response_model=JobRead, status_code=202)
def import_programme(id: UUID, data: ProgrammeImport, session: SessionDep, _writer: Writer):
    programme = require_programme(session, id)
    manifest = data.model_dump(exclude={"is_synthetic", "idempotency_key"})
    return enqueue_import(
        session,
        programme.institution_id,
        CatalogueImport(
            is_synthetic=data.is_synthetic,
            idempotency_key=data.idempotency_key,
            programmes=[manifest],
        ),
        target_id=id,
    )


@router.get("/catalogue/jobs/{id}", response_model=JobRead)
def read_job(id: UUID, session: SessionDep):
    return require_job(session, id)


@router.get("/programmes/{id}/coverage", response_model=CoverageRead)
def programme_coverage(id: UUID, session: SessionDep, revision_id: UUID | None = None):
    return coverage(session, id, revision_id)


@router.get("/programmes/{id}/revisions", response_model=Page[ProgrammeRevisionRead])
def programme_revisions(
    id: UUID,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return revision_list(session, id, limit, offset)


@router.get("/programmes/{id}/revisions/{revision_id}/courses", response_model=CoursePage)
def revision_courses(
    id: UUID,
    revision_id: UUID,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return list_courses(session, id, limit, offset, revision_id)
