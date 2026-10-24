"""Protected immutable academic plans and version-bound operator review."""

from datetime import datetime
from typing import Any, Generic, TypeVar
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
from shiftos.core.access import require_api_access
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import Job
from shiftos.repositories import pathways
from shiftos.schemas.analysis import EvidenceItem, Key
from shiftos.schemas.common import ErrorResponse, Page
from shiftos.schemas.pathways import (
    AcademicPathway,
    FutureScenario,
    LearningResource,
    PathwayStep,
    PlanRequest,
    PlanResult,
    PlanReviewRequest,
    ScenarioComparison,
    SDGAlignment,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Academic action plans"],
    dependencies=[Depends(require_api_access), Depends(require_analysis_access)],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)},
)


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_synthetic: bool
    institution_id: UUID
    programme_id: UUID
    programme_revision_id: UUID
    career_run_id: UUID
    career_fingerprint: str
    job_id: UUID
    mode: str
    status: JobStatus
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    request_json: dict[str, Any]
    manifest_json: dict[str, Any]
    result_json: PlanResult | dict[str, Any] = Field(
        description=(
            "Completed validated PlanResult, or an empty/pending/withheld metadata object. "
            "The metadata alternative does not establish a validated academic result."
        )
    )
    model_usage_json: dict[str, Any]
    fingerprint: str | None
    method_version: str | None
    schema_version: str | None
    model_name: str | None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class PlanReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    is_synthetic: bool
    plan_run_id: UUID
    programme_revision_id: UUID
    plan_fingerprint: str
    actor: str
    decision: str
    reason: str
    reviewed_at: datetime
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


T = TypeVar("T")


class PlanSection(Page[T], Generic[T]):  # noqa: UP046 - match the existing Pydantic page contract
    status: JobStatus
    error: str | None = None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class ComparisonRead(BaseModel):
    status: JobStatus
    error: str | None = None
    comparison: ScenarioComparison | None = None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


def _job(session, run):
    job = session.get(Job, run.job_id)
    if job is None:
        raise DomainError("NOT_FOUND", "Action-plan job was not found", 404)
    return job


def _visibility(session, run, settings):
    allowed, limitations = pathways.access_state(session, run, settings)
    if allowed and any(
        item.get("rights", {}).get("excerpt_output_allowed") is not True
        for item in run.manifest_json.get("packet", {}).get("references", [])
    ):
        return False, ["A contributing source denies excerpt output; derived text is withheld"]
    return allowed, limitations


def _withheld(value):
    return {"source_text_withheld": True, "revalidation_required": True} if value else {}


def plan_response(session, run, settings):
    job = _job(session, run)
    allowed, limitations = _visibility(session, run, settings)
    permitted = _permitted_quotes(run.manifest_json) if allowed else set()
    response = {
        key: getattr(run, key)
        for key in PlanRead.model_fields
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
        response[key] = (
            _public_metadata(getattr(run, key), permitted)
            if allowed
            else _withheld(getattr(run, key))
        )
    response.update(
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        needs_evidence_revalidation=not allowed,
        evidence_access_limitations=limitations,
    )
    return response


def _section(session, run, section, settings, limit, offset, *, pathway_key=None):
    job = _job(session, run)
    allowed, limitations = _visibility(session, run, settings)
    values = []
    if allowed:
        values = run.result_json.get(section, [])
        if pathway_key is not None:
            found = next((item for item in values if item.get("key") == pathway_key), None)
            if found is None:
                raise DomainError("NOT_FOUND", "The pathway was not found in this plan", 404)
            values = found["steps"]
        values = _public_metadata(values, _permitted_quotes(run.manifest_json))
    return {
        "status": job.status,
        "error": job.error,
        "items": values[offset : offset + limit],
        "total": len(values),
        "limit": limit,
        "offset": offset,
        "needs_evidence_revalidation": not allowed,
        "evidence_access_limitations": limitations,
    }


@router.post("/career-analyses/{id}/action-plans", response_model=PlanRead, status_code=202)
def create_plan(id: UUID, data: PlanRequest, request: Request, session: SessionDep):
    return plan_response(
        session,
        pathways.enqueue_plan(session, id, data, request.app.state.settings),
        request.app.state.settings,
    )


@router.get("/career-analyses/{id}/action-plans", response_model=Page[PlanRead])
def plan_history(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    result = pathways.plan_history(session, id, limit, offset)
    result["items"] = [
        plan_response(session, row, request.app.state.settings) for row in result["items"]
    ]
    return result


@router.get("/action-plans/{id}", response_model=PlanRead)
def read_plan(id: UUID, request: Request, session: SessionDep):
    return plan_response(session, pathways.get_plan(session, id), request.app.state.settings)


@router.get("/action-plans/{id}/pathways", response_model=PlanSection[AcademicPathway])
def read_pathways(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _section(
        session,
        pathways.get_plan(session, id),
        "pathways",
        request.app.state.settings,
        limit,
        offset,
    )


@router.get("/action-plans/{id}/pathways/{key}/steps", response_model=PlanSection[PathwayStep])
def read_steps(
    id: UUID, key: Key, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _section(
        session,
        pathways.get_plan(session, id),
        "pathways",
        request.app.state.settings,
        limit,
        offset,
        pathway_key=key,
    )


@router.get("/action-plans/{id}/resources", response_model=PlanSection[LearningResource])
def read_resources(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _section(
        session,
        pathways.get_plan(session, id),
        "resources",
        request.app.state.settings,
        limit,
        offset,
    )


@router.get("/action-plans/{id}/scenarios", response_model=PlanSection[FutureScenario])
def read_scenarios(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _section(
        session,
        pathways.get_plan(session, id),
        "scenarios",
        request.app.state.settings,
        limit,
        offset,
    )


@router.get("/action-plans/{id}/sdg", response_model=PlanSection[SDGAlignment])
def read_sdgs(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _section(
        session,
        pathways.get_plan(session, id),
        "sdg_alignments",
        request.app.state.settings,
        limit,
        offset,
    )


@router.get("/action-plans/{id}/evidence", response_model=PlanSection[EvidenceItem])
def read_evidence(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    return _section(
        session,
        pathways.get_plan(session, id),
        "evidence",
        request.app.state.settings,
        limit,
        offset,
    )


@router.get("/action-plans/{id}/comparison", response_model=ComparisonRead)
def read_comparison(id: UUID, request: Request, session: SessionDep):
    run = pathways.get_plan(session, id)
    job = _job(session, run)
    allowed, limitations = _visibility(session, run, request.app.state.settings)
    value = run.result_json.get("comparison") if allowed else None
    return {
        "status": job.status,
        "error": job.error,
        "comparison": _public_metadata(value, _permitted_quotes(run.manifest_json))
        if value is not None
        else None,
        "needs_evidence_revalidation": not allowed,
        "evidence_access_limitations": limitations,
    }


def review_response(session, row, settings):
    run = pathways.get_plan(session, row.plan_run_id)
    allowed, limitations = _visibility(session, run, settings)
    response = PlanReviewRead.model_validate(row)
    if not allowed:
        response.reason = "Review reason withheld pending source and parent revalidation"
    response.needs_evidence_revalidation = not allowed
    response.evidence_access_limitations = limitations
    return response


@router.post("/action-plans/{id}/reviews", response_model=PlanReviewRead, status_code=201)
def create_review(id: UUID, data: PlanReviewRequest, request: Request, session: SessionDep):
    return review_response(
        session,
        pathways.append_review(session, id, data, request.app.state.settings),
        request.app.state.settings,
    )


@router.get("/action-plans/{id}/reviews", response_model=Page[PlanReviewRead])
def read_reviews(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    result = pathways.review_history(session, id, limit, offset)
    result["items"] = [
        review_response(session, row, request.app.state.settings) for row in result["items"]
    ]
    return result
