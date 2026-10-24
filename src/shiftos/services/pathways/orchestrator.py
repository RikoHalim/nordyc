"""Use the existing worker for bounded, versioned academic action plans."""

from datetime import UTC, datetime

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.repositories.pathways import (
    access_state,
    lock_plan_for_job,
    persist_result,
    source_signatures,
)
from shiftos.schemas.pathways import PlanRequest, PlanResult


def process_plan_job(database, job, settings):
    from shiftos.services.pathways.engine import evaluate

    with database.session_factory() as session:
        run, _ = lock_plan_for_job(session, job.id, settings)
        request = PlanRequest.model_validate(run.request_json)
        result = PlanResult.model_validate(
            evaluate(session, run.career_run_id, request, settings, request.as_of)
        )
        manifest = dict(run.manifest_json)
        manifest.update(
            permission_policy=result.permission_policy,
            packet={"references": [item.model_dump(mode="json") for item in result.evidence]},
        )
        manifest["source_signatures"] = source_signatures(session, manifest["packet"]["references"])
        run_id = run.id
    if request.mode == "live":
        from shiftos.services.pathways.reasoning import explain

        result = PlanResult.model_validate(explain(result, settings))
    with database.session_factory() as session:
        run, stored_job = lock_plan_for_job(session, job.id, settings)
        if run.id != run_id:
            raise DomainError("CONFLICT", "Action-plan identity changed while processing", 409)
        run.manifest_json = manifest
        allowed, _ = access_state(session, run, settings, for_update=True)
        if not allowed:
            raise DomainError(
                "CONFLICT", "Action-plan sources or policy changed while processing", 409
            )
        persist_result(session, run, result, settings)
        stored_job.status = (
            JobStatus.SUCCEEDED if result.status == "supported" else JobStatus.PARTIAL
        )
        stored_job.completed_at, stored_job.error = datetime.now(UTC), None
        stored_job.result_json = {
            "action_plan_id": str(run.id),
            "status": result.status,
            "fingerprint": run.fingerprint,
            "pathway_count": len(result.pathways),
            "scenario_count": len(result.scenarios),
        }
        session.commit()
