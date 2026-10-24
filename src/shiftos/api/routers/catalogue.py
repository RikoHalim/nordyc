"""Catalogue jobs, structured fallback and reproducible revision access."""

import hmac
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import HttpUrl, ValidationError
from sqlalchemy.orm import Session

from shiftos.core.access import authenticate, require_api_access, require_permission
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
    dependencies=[Depends(require_api_access)],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 413, 422, 503)},
)
SessionDep = Annotated[Session, Depends(get_session)]


def require_writer(
    request: Request, x_catalogue_token: Annotated[str | None, Header()] = None
) -> None:
    principal = authenticate(request)
    if principal is not None:
        require_permission(principal, "write")
        return
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


@router.post(
    "/programmes/{id}/curriculum-pdf",
    response_model=JobRead,
    status_code=202,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def upload_curriculum_pdf(
    id: UUID,
    request: Request,
    session: SessionDep,
    _writer: Writer,
    source_url: HttpUrl | None = None,
    regions: Annotated[str | None, Query(max_length=15000)] = None,
):
    """Upload application/pdf; optional regions is a JSON list of page rectangles."""
    from shiftos.services.ingestion.pdf import PdfCourseRegion
    from shiftos.services.ingestion.uploads import enqueue_pdf_upload

    if request.headers.get("content-type", "").split(";", 1)[0] != "application/pdf":
        raise DomainError(
            "UNSUPPORTED_MEDIA_TYPE", "Upload the original PDF as application/pdf", 415
        )
    try:
        supplied = json.loads(regions) if regions is not None else None
        if supplied is not None and (
            not isinstance(supplied, list) or not 1 <= len(supplied) <= 50
        ):
            raise ValueError
        selected = [PdfCourseRegion.model_validate(r) for r in supplied] if supplied else None
    except (ValueError, ValidationError, TypeError):
        raise DomainError(
            "VALIDATION_ERROR", "Supply between 1 and 50 valid PDF regions", 422
        ) from None
    content = await request.body()
    from starlette.concurrency import run_in_threadpool

    return await run_in_threadpool(
        enqueue_pdf_upload,
        session,
        id,
        content,
        request.app.state.settings,
        source_url=str(source_url) if source_url else None,
        regions=selected,
    )


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
def read_job(
    id: UUID,
    request: Request,
    session: SessionDep,
    x_analysis_token: Annotated[str | None, Header()] = None,
):
    job = require_job(session, id)
    if job.kind in {"PROGRAMME_ANALYSIS", "CAREER_ANALYSIS", "ACTION_PLAN"}:
        from shiftos.api.routers.analysis import require_analysis_access

        require_analysis_access(request, x_analysis_token)
        response = JobRead.model_validate(job)
        response.result = (
            {
                "source_content_withheld": True,
                "detail": "Read results through the protected analysis resource",
            }
            if job.result_json
            else {}
        )
        return response
    return job


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
