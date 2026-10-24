"""Protected programme-analysis queue and inspection; no provider calls in HTTP."""

import hmac
import json
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from shiftos.core.access import authenticate, require_api_access
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.db.session import get_session
from shiftos.models import (
    AnalysisRun,
    CourseFinding,
    DatasetVersion,
    Document,
    DocumentAnchor,
    EvidenceReference,
    Job,
)
from shiftos.repositories import analysis
from shiftos.repositories.catalogue import digest
from shiftos.schemas.analysis import AnalysisRequest, CourseFindingResult
from shiftos.schemas.common import ErrorResponse, Page


def require_analysis_access(
    request: Request,
    x_analysis_token: Annotated[str | None, Header()] = None,
) -> None:
    if authenticate(request) is not None:
        return
    token = getattr(request.app.state.settings, "analysis_write_token", None)
    if token is None:
        raise DomainError(
            "ANALYSIS_ACCESS_DISABLED",
            "Configure analysis access before using analysis routes",
            503,
        )
    if not hmac.compare_digest(
        token.get_secret_value().encode(), (x_analysis_token or "").encode()
    ):
        raise DomainError("NOT_AUTHORIZED", "Analysis access authorization required", 401)


router = APIRouter(
    prefix="/api/v1",
    tags=["Programme analysis"],
    dependencies=[Depends(require_api_access), Depends(require_analysis_access)],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)},
)
SessionDep = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


class AnalysisRead(BaseModel):
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
    summary_json: dict[str, Any]
    research_json: dict[str, Any]
    fingerprint: str | None
    model_name: str | None
    prompt_version: str | None
    schema_version: str | None
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    is_synthetic: bool
    run_id: UUID
    course_id: UUID
    programme_revision_id: UUID
    result_json: CourseFindingResult | dict[str, Any] = Field(
        description=(
            "Completed validated CourseFindingResult, "
            "or an empty/pending/withheld metadata object. "
            "The metadata alternative does not establish a validated academic result."
        )
    )
    needs_evidence_revalidation: bool = False
    evidence_access_limitations: list[str] = Field(default_factory=list)


def _permitted_quotes(value) -> set[str]:
    allowed = set()
    if isinstance(value, dict):
        rights = value.get("rights")
        if isinstance(rights, dict) and rights.get("excerpt_output_allowed") is True:
            if isinstance(value.get("id"), str):
                allowed.add(value["id"])
        for item in value.values():
            allowed.update(_permitted_quotes(item))
    elif isinstance(value, list):
        for item in value:
            allowed.update(_permitted_quotes(item))
    return allowed


def _public_metadata(value, permitted: set[str], *, text_allowed: bool = True):
    """Operator access does not itself grant source-text redistribution rights."""
    if isinstance(value, list):
        return [_public_metadata(item, permitted, text_allowed=text_allowed) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    rights = value.get("rights")
    reference = isinstance(rights, dict)
    disclose_reference = text_allowed and reference and rights.get("excerpt_output_allowed") is True
    for key, item in value.items():
        if key in {
            "raw",
            "text",
            "content",
            "prompt",
            "private_content",
            "api_key",
            "authorization",
        }:
            continue
        if key == "quote" and value.get("reference_id") not in permitted:
            continue
        if key == "excerpt" and not disclose_reference:
            continue
        if (
            reference
            and not disclose_reference
            and key
            in {
                "facts",
                "statement",
                "description",
                "task",
                "capability",
            }
        ):
            continue
        result[key] = _public_metadata(item, permitted, text_allowed=text_allowed)
    return result


def _withdrawn(metadata) -> bool:
    return not isinstance(metadata, dict) or any(
        metadata.get(key)
        for key in (
            "rights_withdrawn",
            "retracted",
            "superseded",
            "correction_pending",
        )
    )


def _source_state(session: Session, run: AnalysisRun) -> tuple[bool, list[str]]:
    """Bounded current status checks; the frozen historical result is never rewritten."""
    packet = run.manifest_json.get("packet")
    pointers = packet.get("references") if isinstance(packet, dict) else None
    if not isinstance(pointers, list) or len(pointers) > 300:
        return False, ["Frozen reference inventory is missing or invalid; revalidation is required"]
    expected, syllabus = {}, {}
    try:
        for pointer in pointers:
            if not isinstance(pointer, dict):
                raise ValueError
            reference_id = UUID(str(pointer["evidence_reference_id"]))
            version_id = UUID(str(pointer["version_id"]))
            identities = syllabus if pointer.get("kind") == "syllabus" else expected
            if reference_id in identities and identities[reference_id] != version_id:
                raise ValueError
            identities[reference_id] = version_id
    except (KeyError, TypeError, ValueError):
        return False, ["Frozen reference identity is missing or invalid; revalidation is required"]
    references = (
        {
            row.id: row
            for row in session.scalars(
                select(EvidenceReference).where(EvidenceReference.id.in_(expected))
            )
        }
        if expected
        else {}
    )
    versions = (
        {
            row.id: row
            for row in session.scalars(
                select(DatasetVersion).where(DatasetVersion.id.in_(set(expected.values())))
            )
        }
        if expected
        else {}
    )
    for reference_id, version_id in expected.items():
        reference, version = references.get(reference_id), versions.get(version_id)
        if (
            reference is None
            or version is None
            or reference.version_id != version_id
            or reference.is_synthetic != run.is_synthetic
            or version.is_synthetic != run.is_synthetic
            or reference.review_status == "rejected"
            or _withdrawn(reference.metadata_json)
            or _withdrawn(version.metadata_json)
        ):
            return False, [
                "A source reference was removed, rejected or flagged; revalidation is required"
            ]
    anchors = (
        {
            row.id: row
            for row in session.scalars(
                select(DocumentAnchor).where(DocumentAnchor.id.in_(syllabus))
            )
        }
        if syllabus
        else {}
    )
    documents = (
        {
            row.id: row
            for row in session.scalars(
                select(Document).where(
                    Document.id.in_({anchor.document_id for anchor in anchors.values()})
                )
            )
        }
        if anchors
        else {}
    )
    for anchor_id, revision_id in syllabus.items():
        anchor = anchors.get(anchor_id)
        document = documents.get(anchor.document_id) if anchor else None
        if (
            anchor is None
            or document is None
            or document.programme_revision_id != revision_id
            or revision_id != run.programme_revision_id
            or _withdrawn(document.metadata_json)
            or document.metadata_json.get("content_reviewed") is not True
        ):
            return False, ["A syllabus reference changed or was flagged; revalidation is required"]
    return True, []


def _access_state(session: Session, run: AnalysisRun, settings) -> tuple[bool, list[str]]:
    frozen = run.manifest_json.get("permission_policy")
    if not isinstance(frozen, dict) or not frozen.get("version") or not frozen.get("sha256"):
        return False, ["Frozen source-use policy is missing; source text requires revalidation"]
    try:
        path = settings.analysis_permissions_path
        if path.stat().st_size > 100_000:
            raise ValueError
        policy = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(policy, dict) or not isinstance(policy.get("sources"), dict):
            raise ValueError
        if policy.get("version") != frozen["version"] or digest(policy) != frozen["sha256"]:
            return False, ["Source-use policy changed; source text requires revalidation"]
    except (AttributeError, OSError, TypeError, ValueError):
        return False, ["Current source-use policy is unavailable; source text is withheld"]
    return _source_state(session, run)


def analysis_response(session: Session, run: AnalysisRun, settings=None) -> dict:
    job = session.get(Job, run.job_id)
    if job is None:
        raise DomainError("NOT_FOUND", "Analysis job was not found", 404)
    text_allowed, limitations = _access_state(session, run, settings)
    permitted = _permitted_quotes(run.manifest_json) if text_allowed else set()
    return {
        **{
            key: getattr(run, key)
            for key in AnalysisRead.model_fields
            if key
            not in {
                "status",
                "started_at",
                "completed_at",
                "error",
                "needs_evidence_revalidation",
                "evidence_access_limitations",
            }
        },
        "status": job.status,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error": job.error,
        **{
            key: _public_metadata(getattr(run, key), permitted, text_allowed=text_allowed)
            for key in (
                "request_json",
                "manifest_json",
                "summary_json",
                "research_json",
            )
        },
        "needs_evidence_revalidation": not text_allowed,
        "evidence_access_limitations": limitations,
    }


def finding_response(
    run: AnalysisRun,
    finding: CourseFinding,
    *,
    access_state: tuple[bool, list[str]],
) -> FindingRead:
    response = FindingRead.model_validate(finding)
    text_allowed, limitations = access_state
    response.result_json = _public_metadata(
        finding.result_json,
        _permitted_quotes(run.manifest_json) if text_allowed else set(),
        text_allowed=text_allowed,
    )
    response.needs_evidence_revalidation = not text_allowed
    response.evidence_access_limitations = limitations
    return response


@router.post("/programmes/{id}/analyses", response_model=AnalysisRead, status_code=202)
def create_analysis(id: UUID, data: AnalysisRequest, request: Request, session: SessionDep):
    return analysis_response(
        session, analysis.enqueue_analysis(session, id, data), request.app.state.settings
    )


@router.get("/programmes/{id}/analyses", response_model=Page[AnalysisRead])
def programme_analyses(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    result = analysis.analysis_history(session, id, limit, offset)
    result["items"] = [
        analysis_response(session, run, request.app.state.settings) for run in result["items"]
    ]
    return result


@router.get("/analyses/{id}", response_model=AnalysisRead)
def read_analysis(id: UUID, request: Request, session: SessionDep):
    return analysis_response(
        session, analysis.get_analysis(session, id), request.app.state.settings
    )


@router.get("/analyses/{id}/courses", response_model=Page[FindingRead])
def read_courses(
    id: UUID, request: Request, session: SessionDep, limit: Limit = 50, offset: Offset = 0
):
    run = analysis.get_analysis(session, id)
    result = analysis.analysis_courses(session, id, limit, offset)
    access_state = _access_state(session, run, request.app.state.settings)
    result["items"] = [
        finding_response(run, row, access_state=access_state) for row in result["items"]
    ]
    return result


@router.get("/analyses/{id}/courses/{course_id}", response_model=FindingRead)
def read_course(id: UUID, course_id: UUID, request: Request, session: SessionDep):
    run = analysis.get_analysis(session, id)
    return finding_response(
        run,
        analysis.analysis_course(session, id, course_id),
        access_state=_access_state(session, run, request.app.state.settings),
    )
