"""Protected asynchronous career alignment and append-only academic review."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from shiftos.api.routers.analysis import (
    Limit,
    Offset,
    SessionDep,
    _permitted_quotes,
    _public_metadata,
    require_analysis_access,
)
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import CareerRecommendation, CareerRun, Job
from shiftos.repositories import career
from shiftos.schemas.analysis import EvidenceItem
from shiftos.schemas.career import (
    CareerRequest,
    OccupationAlignment,
    RequirementFinding,
    ReviewRequest,
)
from shiftos.schemas.common import ErrorResponse, Page

router = APIRouter(
    prefix="/api/v1",
    tags=["Career alignment"],
    dependencies=[Depends(require_analysis_access)],
    responses={code: {"model": ErrorResponse} for code in (401, 404, 409, 422, 503)},
)


class CareerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_synthetic: bool
    institution_id: UUID
    programme_id: UUID
    programme_revision_id: UUID
    job_id: UUID
    mode: str
    status: JobStatus
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    request_json: dict[str, Any]
    manifest_json: dict[str, Any]
    result_json: dict[str, Any]
    model_usage_json: dict[str, Any]
    fingerprint: str | None
    method_version: str | None
    schema_version: str | None
    model_name: str | None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_synthetic: bool
    run_id: UUID
    programme_revision_id: UUID
    recommendation_key: str
    version_sha256: str
    result_json: dict[str, Any]
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    is_synthetic: bool
    recommendation_id: UUID
    run_id: UUID
    programme_revision_id: UUID
    recommendation_version: str
    actor: str
    decision: str
    reason: str
    reviewed_at: datetime
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class RecommendationPage(Page[RecommendationRead]):
    status: JobStatus
    error: str | None = None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class OccupationPage(Page[OccupationAlignment]):
    status: JobStatus
    error: str | None = None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class CompetencyPage(Page[RequirementFinding]):
    status: JobStatus
    error: str | None = None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class EvidencePage(Page[EvidenceItem]):
    status: JobStatus
    error: str | None = None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


def _visibility(session, run, settings):
    allowed, limitations = career.access_state(session, run, settings)
    if allowed and any(
        pointer.get("rights", {}).get("excerpt_output_allowed") is not True
        for pointer in run.manifest_json.get("packet", {}).get("references", [])
    ):
        return False, [
            "A contributing source does not permit excerpt output; derived source text is withheld"
        ]
    return allowed, limitations


def _withheld(value):
    # Historical records remain unchanged. Current API disclosures avoid derived source prose.
    return {"source_text_withheld": True, "revalidation_required": True} if value else {}


def career_response(session, run: CareerRun, settings):
    job = session.get(Job, run.job_id)
    if job is None:
        raise DomainError("NOT_FOUND", "Career analysis job was not found", 404)
    allowed, limitations = _visibility(session, run, settings)
    permitted = _permitted_quotes(run.manifest_json) if allowed else set()
    result = {
        key: getattr(run, key)
        for key in CareerRead.model_fields
        if key
        not in {
            "status",
            "started_at",
            "completed_at",
            "error",
            "needs_evidence_revalidation",
            "evidence_access_limitations",
        }
    }
    for key in ("request_json", "manifest_json", "result_json", "model_usage_json"):
        result[key] = (
            _public_metadata(getattr(run, key), permitted)
            if allowed
            else _withheld(getattr(run, key))
        )
    result.update(
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        needs_evidence_revalidation=not allowed,
        evidence_access_limitations=limitations,
    )
    return result


def recommendation_response(session, run: CareerRun, row: CareerRecommendation, settings):
    allowed, limitations = _visibility(session, run, settings)
    response = RecommendationRead.model_validate(row)
    response.result_json = (
        _public_metadata(row.result_json, _permitted_quotes(run.manifest_json))
        if allowed
        else _withheld(row.result_json)
    )
    response.needs_evidence_revalidation = not allowed
    response.evidence_access_limitations = limitations
    return response


@router.post("/programmes/{id}/career-analyses", response_model=CareerRead, status_code=202)
def create_career(id: UUID, data: CareerRequest, request: Request, session: SessionDep):
    return career_response(
        session, career.enqueue_career(session, id, data), request.app.state.settings
    )


@router.get("/programmes/{id}/career-analyses", response_model=Page[CareerRead])
def programme_career_history(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    result = career.career_history(session, id, limit, offset)
    result["items"] = [
        career_response(session, row, request.app.state.settings) for row in result["items"]
    ]
    return result


@router.get("/career-analyses/{id}", response_model=CareerRead)
def read_career(id: UUID, request: Request, session: SessionDep):
    return career_response(session, career.get_career(session, id), request.app.state.settings)


def _result_page(id, section, request, session, limit, offset):
    run = career.get_career(session, id)
    job = session.get(Job, run.job_id)
    if job is None:
        raise DomainError("NOT_FOUND", "Career analysis job was not found", 404)
    allowed, limitations = _visibility(session, run, request.app.state.settings)
    values = run.result_json.get(section, [])
    if not allowed:
        return {
            "status": job.status,
            "error": job.error,
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "needs_evidence_revalidation": True,
            "evidence_access_limitations": limitations,
        }
    return {
        "status": job.status,
        "error": job.error,
        "items": _public_metadata(
            values[offset : offset + limit], _permitted_quotes(run.manifest_json)
        ),
        "total": len(values),
        "limit": limit,
        "offset": offset,
        "needs_evidence_revalidation": False,
        "evidence_access_limitations": [],
    }


@router.get("/career-analyses/{id}/occupations", response_model=OccupationPage)
def read_occupations(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _result_page(id, "occupations", request, session, limit, offset)


@router.get("/career-analyses/{id}/competencies", response_model=CompetencyPage)
def read_competencies(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _result_page(id, "competencies", request, session, limit, offset)


@router.get("/career-analyses/{id}/evidence", response_model=EvidencePage)
def read_evidence(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _result_page(id, "evidence", request, session, limit, offset)


@router.get("/career-analyses/{id}/recommendations", response_model=RecommendationPage)
def read_recommendations(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    run = career.get_career(session, id)
    job = session.get(Job, run.job_id)
    if job is None:
        raise DomainError("NOT_FOUND", "Career analysis job was not found", 404)
    allowed, limitations = _visibility(session, run, request.app.state.settings)
    result = career.recommendations(session, id, limit, offset)
    result.update(
        status=job.status,
        error=job.error,
        needs_evidence_revalidation=not allowed,
        evidence_access_limitations=limitations,
    )
    result["items"] = [
        recommendation_response(session, run, row, request.app.state.settings)
        for row in result["items"]
    ]
    return result


@router.post("/career-recommendations/{id}/reviews", response_model=ReviewRead, status_code=201)
def review_recommendation(id: UUID, data: ReviewRequest, request: Request, session: SessionDep):
    row = career.append_review(session, id, data, request.app.state.settings)
    return review_response(session, row, request.app.state.settings)


def review_response(session, row, settings):
    run = career.get_career(session, row.run_id)
    allowed, limitations = _visibility(session, run, settings)
    response = ReviewRead.model_validate(row)
    if not allowed:
        response.reason = "Review reason withheld pending source revalidation"
    response.needs_evidence_revalidation = not allowed
    response.evidence_access_limitations = limitations
    return response


@router.get("/career-recommendations/{id}/reviews", response_model=Page[ReviewRead])
def recommendation_reviews(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    result = career.review_history(session, id, limit, offset)
    result["items"] = [
        review_response(session, row, request.app.state.settings) for row in result["items"]
    ]
    return result
