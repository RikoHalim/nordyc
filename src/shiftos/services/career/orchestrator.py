"""Execute career jobs in the existing worker and commit results atomically."""

from datetime import UTC, datetime

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.repositories.career import (
    access_state,
    lock_career_for_job,
    persist_result,
    source_signatures,
)
from shiftos.schemas.career import CareerRequest, CareerResult


def process_career_job(database, job, settings):
    from shiftos.services.career.engine import evaluate

    with database.session_factory() as session:
        run, _ = lock_career_for_job(session, job.id)
        request = CareerRequest.model_validate(run.request_json)
        result = evaluate(
            session, run.programme_id, run.programme_revision_id, request, settings, request.as_of
        )
        result = CareerResult.model_validate(result)
        manifest = dict(run.manifest_json)
        manifest.update(
            packet={"references": [item.model_dump(mode="json") for item in result.evidence]},
            permission_policy=result.permission_policy,
        )
        manifest["source_signatures"] = source_signatures(session, manifest["packet"]["references"])
        # Keep the evaluated snapshot detached from the slow external model operation.
        run_id, manifest_before = run.id, manifest
    if request.mode == "live":
        from shiftos.services.career.reasoning import explain

        result = CareerResult.model_validate(explain(result, settings))
    with database.session_factory() as session:
        run, stored_job = lock_career_for_job(session, job.id)
        if run.id != run_id:
            raise DomainError("CONFLICT", "Career run identity changed", 409)
        run.manifest_json = manifest_before
        allowed, _ = access_state(session, run, settings, for_update=True)
        if not allowed:
            raise DomainError(
                "CONFLICT",
                "Career sources or policy changed while processing; submit a new run",
                409,
            )
        persist_result(session, run, result)
        stored_job.status = (
            JobStatus.SUCCEEDED if result.status == "supported" else JobStatus.PARTIAL
        )
        stored_job.completed_at, stored_job.error = datetime.now(UTC), None
        stored_job.result_json = {
            "career_run_id": str(run.id),
            "status": result.status,
            "course_count": len(result.course_ids),
            "recommendation_count": len(result.recommendations),
            "fingerprint": run.fingerprint,
        }
        session.commit()
