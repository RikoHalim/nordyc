"""Administrative queueing and owned immutable-result persistence, without network I/O."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import AnalysisRun, Course, CourseFinding, Job, ProgrammeRevision
from shiftos.repositories.catalogue import digest, lock_institution
from shiftos.schemas.academic import CourseRead
from shiftos.services.academic import require_programme

if TYPE_CHECKING:
    from shiftos.schemas.analysis import AnalysisRequest

TERMINAL = {JobStatus.SUCCEEDED, JobStatus.PARTIAL, JobStatus.FAILED}


def inventory_snapshot(session: Session, revision_id: UUID) -> list[dict]:
    courses = session.scalars(
        select(Course).where(Course.programme_revision_id == revision_id).order_by(Course.id)
    ).all()
    return [CourseRead.model_validate(course).model_dump(mode="json") for course in courses]


def enqueue_analysis(
    session: Session,
    programme_id: UUID,
    request: AnalysisRequest,
) -> AnalysisRun:
    programme = require_programme(session, programme_id)
    institution = lock_institution(session, programme.institution_id)
    session.refresh(programme)
    intent = {
        "programme_id": str(programme_id),
        "request": request.model_dump(mode="json", exclude={"idempotency_key"}),
    }
    if request.idempotency_key:
        existing_job = session.scalar(
            select(Job).where(
                Job.institution_id == institution.id,
                Job.kind == "PROGRAMME_ANALYSIS",
                Job.idempotency_key == request.idempotency_key,
            )
        )
        if existing_job:
            if existing_job.payload_json != intent:
                raise DomainError(
                    "CONFLICT", "Analysis idempotency key has different request content", 409
                )
            existing = session.scalar(
                select(AnalysisRun).where(AnalysisRun.job_id == existing_job.id)
            )
            if existing is None:
                raise DomainError(
                    "CONFLICT", "Analysis job has no run; administrator review required", 409
                )
            return existing
    revision_id = request.revision_id or programme.active_revision_id
    revision = session.get(ProgrammeRevision, revision_id) if revision_id else None
    if revision is None or revision.programme_id != programme.id:
        raise DomainError("NOT_FOUND", "Selected programme revision was not found", 404)
    courses = session.scalars(
        select(Course).where(Course.programme_revision_id == revision.id).order_by(Course.id)
    ).all()
    if not courses:
        raise DomainError("CONFLICT", "Import a nonempty course inventory before analysis", 409)
    if not (institution.is_synthetic == programme.is_synthetic == revision.is_synthetic):
        raise DomainError("CONFLICT", "Programme snapshot has inconsistent synthetic lineage", 409)
    if any(course.is_synthetic != programme.is_synthetic for course in courses):
        raise DomainError("CONFLICT", "Course inventory has inconsistent synthetic lineage", 409)
    inventory = inventory_snapshot(session, revision.id)
    job = Job(
        institution_id=institution.id,
        programme_revision_id=revision.id,
        kind="PROGRAMME_ANALYSIS",
        payload_json=intent,
        idempotency_key=request.idempotency_key,
        is_synthetic=programme.is_synthetic,
    )
    session.add(job)
    session.flush()
    resolved = request.model_dump(mode="json", exclude={"idempotency_key"})
    resolved["revision_id"] = str(revision.id)
    run = AnalysisRun(
        institution_id=institution.id,
        programme_id=programme.id,
        programme_revision_id=revision.id,
        job_id=job.id,
        mode=request.mode,
        request_json=resolved,
        manifest_json={
            "inventory": inventory,
            "inventory_hash": digest(inventory),
            "programme_name": programme.name,
            "version_label": revision.version_label,
            "import_fingerprint": revision.import_fingerprint,
            "is_synthetic": programme.is_synthetic,
        },
        is_synthetic=programme.is_synthetic,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_analysis(session: Session, run_id: UUID) -> AnalysisRun:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise DomainError("NOT_FOUND", "Analysis run was not found", 404)
    return run


def lock_analysis_for_job(session: Session, job_id: UUID) -> AnalysisRun:
    job = session.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None or job.kind != "PROGRAMME_ANALYSIS":
        raise DomainError("NOT_FOUND", "Analysis job was not found", 404)
    if job.status != JobStatus.RUNNING:
        raise DomainError("CONFLICT", "Analysis job is not running; results remain immutable", 409)
    run = session.scalar(select(AnalysisRun).where(AnalysisRun.job_id == job.id).with_for_update())
    if run is None:
        raise DomainError("NOT_FOUND", "Analysis run was not found", 404)
    if (
        run.programme_revision_id != job.programme_revision_id
        or run.institution_id != job.institution_id
        or run.is_synthetic != job.is_synthetic
    ):
        raise DomainError("CONFLICT", "Analysis job and snapshot ownership disagree", 409)
    return run


def replace_findings(session: Session, run: AnalysisRun, findings: list[dict]) -> None:
    """Replace active-job results atomically; callers validate the result schema first."""
    locked = lock_analysis_for_job(session, run.job_id)
    inventory = locked.manifest_json.get("inventory", locked.manifest_json.get("courses", []))
    try:
        expected = {UUID(str(item.get("id", item.get("course_id")))) for item in inventory}
        supplied = [UUID(str(item.get("course_id", item.get("id")))) for item in findings]
    except (ValueError, TypeError, AttributeError) as exc:
        raise DomainError("VALIDATION_ERROR", "Invalid analysis course identity", 422) from exc
    if not expected or len(supplied) != len(set(supplied)) or set(supplied) != expected:
        raise DomainError("CONFLICT", "Findings must cover every frozen course exactly once", 409)
    owned = set(
        session.scalars(
            select(Course.id).where(
                Course.programme_revision_id == locked.programme_revision_id,
                Course.id.in_(supplied),
            )
        )
    )
    if owned != expected:
        raise DomainError(
            "CONFLICT", "Analysis findings include a course from another snapshot", 409
        )
    session.execute(delete(CourseFinding).where(CourseFinding.run_id == locked.id))
    for course_id, result in zip(supplied, findings, strict=True):
        session.add(
            CourseFinding(
                run_id=locked.id,
                course_id=course_id,
                programme_revision_id=locked.programme_revision_id,
                result_json=deepcopy(result),
                is_synthetic=locked.is_synthetic,
            )
        )
    session.flush()


def analysis_history(session: Session, programme_id: UUID, limit: int, offset: int) -> dict:
    require_programme(session, programme_id)
    query = select(AnalysisRun).where(AnalysisRun.programme_id == programme_id)
    return {
        "items": session.scalars(
            query.order_by(AnalysisRun.created_at.desc(), AnalysisRun.id)
            .limit(limit)
            .offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(query.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }


def analysis_courses(session: Session, run_id: UUID, limit: int, offset: int) -> dict:
    get_analysis(session, run_id)
    query = select(CourseFinding).where(CourseFinding.run_id == run_id)
    return {
        "items": session.scalars(
            query.order_by(CourseFinding.course_id).limit(limit).offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(query.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }


def analysis_course(session: Session, run_id: UUID, course_id: UUID) -> CourseFinding:
    get_analysis(session, run_id)
    finding = session.scalar(
        select(CourseFinding).where(
            CourseFinding.run_id == run_id,
            CourseFinding.course_id == course_id,
        )
    )
    if finding is None:
        raise DomainError("NOT_FOUND", "Course finding was not found in this analysis", 404)
    return finding
