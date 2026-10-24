"""Frozen action-plan queueing, exact parent bindings and append-only review."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import func, inspect, select

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import (
    ActionPlanReview,
    ActionPlanRun,
    AnalysisRun,
    CareerRecommendation,
    CareerReview,
    CareerRun,
    Job,
    PlanRecommendation,
    SDGReference,
)
from shiftos.repositories import career
from shiftos.repositories.analysis import inventory_snapshot
from shiftos.repositories.catalogue import digest, lock_institution


def _conflict(message):
    raise DomainError("CONFLICT", message, 409)


def _phase4_state(session, analysis_id, parent, settings):
    from shiftos.api.routers.analysis import _access_state

    run = session.get(AnalysisRun, analysis_id)
    job = session.get(Job, run.job_id) if run else None
    if (
        run is None
        or job is None
        or (run.programme_id, run.programme_revision_id, run.is_synthetic)
        != (parent.programme_id, parent.programme_revision_id, parent.is_synthetic)
        or job.status not in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
        or not run.fingerprint
    ):
        _conflict("The linked Phase 4 run is not a completed analysis of this revision")
    allowed, _ = _access_state(session, run, settings)
    if not allowed:
        _conflict("The linked Phase 4 evidence requires revalidation")
    return {
        "id": str(run.id),
        "fingerprint": run.fingerprint,
        "summary_sha256": digest(run.summary_json),
        "manifest_sha256": digest(run.manifest_json),
        "job_status": str(job.status),
    }


def _previous_state(session, previous_id, parent):
    previous = session.get(ActionPlanRun, previous_id)
    job = session.get(Job, previous.job_id) if previous else None
    if (
        previous is None
        or job is None
        or previous.programme_id != parent.programme_id
        or previous.is_synthetic != parent.is_synthetic
        or job.status not in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
        or not previous.result_json
        or digest(previous.result_json) != previous.fingerprint
    ):
        _conflict("The previous plan is not a completed snapshot of this programme")
    return {"id": str(previous.id), "fingerprint": previous.fingerprint}


def _review_signature(session, recommendation_ids, *, as_of=None, for_update=False):
    query = select(CareerReview).where(CareerReview.recommendation_id.in_(recommendation_ids))
    if as_of is not None:
        query = query.where(CareerReview.reviewed_at <= as_of)
    query = query.order_by(CareerReview.reviewed_at, CareerReview.id).limit(1001)
    if for_update:
        query = query.with_for_update()
    rows = session.scalars(query.execution_options(populate_existing=True)).all()
    if len(rows) > 1000:
        _conflict("Parent recommendation review history exceeds the bounded plan inventory")
    return digest(
        [
            {
                "id": str(row.id),
                "recommendation_id": str(row.recommendation_id),
                "version": row.recommendation_version,
                "decision": row.decision,
                "reason_sha256": digest(row.reason),
                "actor": row.actor,
                "reviewed_at": row.reviewed_at.isoformat(),
            }
            for row in rows
        ]
    )


def _parent_state(session, run, settings, *, for_update=False):
    parent = session.get(CareerRun, run.career_run_id)
    job = session.get(Job, parent.job_id) if parent else None
    if (
        parent is None
        or job is None
        or job.status not in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
        or not parent.result_json
    ):
        return False, ["The parent career analysis is not completed"]
    if (
        parent.programme_id,
        parent.programme_revision_id,
        parent.institution_id,
        parent.is_synthetic,
    ) != (run.programme_id, run.programme_revision_id, run.institution_id, run.is_synthetic):
        return False, ["Parent career ownership changed"]
    if (
        parent.fingerprint != run.career_fingerprint
        or digest(parent.result_json) != run.career_fingerprint
    ):
        return False, ["Parent career result fingerprint changed"]
    allowed, limitations = career.access_state(session, parent, settings, for_update=for_update)
    if not allowed:
        return False, limitations
    linked = run.manifest_json.get("phase4_parent")
    if linked:
        try:
            if _phase4_state(session, UUID(linked["id"]), parent, settings) != linked:
                return False, ["The linked Phase 4 context changed; a new plan is required"]
        except (DomainError, ValueError, KeyError, TypeError):
            return False, ["The linked Phase 4 context is stale or unavailable"]
    previous = run.manifest_json.get("previous_plan")
    if previous:
        try:
            if _previous_state(session, UUID(previous["id"]), parent) != previous:
                return False, ["The previous frozen plan identity changed"]
        except (DomainError, ValueError, KeyError, TypeError):
            return False, ["The previous plan snapshot is unavailable"]
    bindings = run.manifest_json.get("recommendation_bindings")
    if not isinstance(bindings, list) or not bindings or len(bindings) > 100:
        return False, ["Frozen recommendation bindings are unavailable"]
    try:
        expected = {UUID(str(row["id"])): row["version"] for row in bindings}
        if len(expected) != len(bindings):
            raise ValueError
        query = select(CareerRecommendation).where(CareerRecommendation.id.in_(expected))
        if for_update:
            query = query.with_for_update()
        found = session.scalars(query.execution_options(populate_existing=True)).all()
        if len(found) != len(expected) or any(
            row.run_id != parent.id
            or row.programme_revision_id != parent.programme_revision_id
            or row.is_synthetic != run.is_synthetic
            or row.version_sha256 != expected[row.id]
            or digest(row.result_json) != row.version_sha256
            for row in found
        ):
            raise ValueError
        if _review_signature(session, expected, for_update=for_update) != run.manifest_json.get(
            "parent_review_signature"
        ):
            return False, ["A parent recommendation review changed; a new plan is required"]
    except (KeyError, TypeError, ValueError):
        return False, ["A frozen parent recommendation changed; revalidation is required"]
    return True, []


def enqueue_plan(session, career_run_id: UUID, request, settings):
    parent = career.get_career(session, career_run_id)
    lock_institution(session, parent.institution_id)
    intent = {
        "career_run_id": str(career_run_id),
        "request": request.model_dump(mode="json", exclude={"idempotency_key"}),
    }
    if request.idempotency_key:
        job = session.scalar(
            select(Job).where(
                Job.institution_id == parent.institution_id,
                Job.kind == "ACTION_PLAN",
                Job.idempotency_key == request.idempotency_key,
            )
        )
        if job:
            if job.payload_json != intent:
                _conflict("Action-plan idempotency key has different request content")
            run = session.scalar(select(ActionPlanRun).where(ActionPlanRun.job_id == job.id))
            if run is None:
                _conflict("Action-plan job has no run; administrator review is required")
            return run
    job = session.get(Job, parent.job_id)
    if (
        job is None
        or job.status not in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
        or not parent.result_json
        or not parent.fingerprint
        or digest(parent.result_json) != parent.fingerprint
    ):
        _conflict("Generate a completed validated career analysis before creating an action plan")
    allowed, _ = career.access_state(session, parent, settings, for_update=True)
    if not allowed:
        _conflict("Parent career evidence is stale or restricted; reanalyse before planning")
    rows = session.scalars(
        select(CareerRecommendation)
        .where(CareerRecommendation.run_id == parent.id)
        .order_by(CareerRecommendation.id)
    ).all()
    requested = request.recommendation_ids
    if requested:
        if len(requested) != len(set(requested)):
            _conflict("Select a nonempty unique recommendation inventory")
        owned = {row.id: row for row in rows}
        if not set(requested) <= set(owned):
            _conflict("Selected recommendations belong to another career run")
        rows = [owned[value] for value in requested]
    if not rows or len(rows) > 100:
        _conflict("A bounded nonempty career recommendation inventory is required")
    if any(
        row.programme_revision_id != parent.programme_revision_id
        or row.is_synthetic != parent.is_synthetic
        or digest(row.result_json) != row.version_sha256
        for row in rows
    ):
        _conflict("Recommendation versions do not match their career snapshot")
    cutoff = request.as_of or datetime.now(UTC)
    review_signature = _review_signature(session, [row.id for row in rows], as_of=cutoff)
    if review_signature != _review_signature(session, [row.id for row in rows]):
        _conflict("Later recommendation reviews exist; use a current planning cutoff")
    resolved = request.model_dump(mode="json", exclude={"idempotency_key"})
    resolved.update(as_of=cutoff.isoformat(), recommendation_ids=[str(row.id) for row in rows])
    manifest = {
        "inventory_hash": parent.manifest_json.get("inventory_hash"),
        "career_fingerprint": parent.fingerprint,
        "recommendation_bindings": [
            {"id": str(row.id), "key": row.recommendation_key, "version": row.version_sha256}
            for row in rows
        ],
        "parent_review_signature": review_signature,
    }
    if request.phase4_analysis_id:
        manifest["phase4_parent"] = _phase4_state(
            session, request.phase4_analysis_id, parent, settings
        )
    if request.previous_plan_id:
        manifest["previous_plan"] = _previous_state(session, request.previous_plan_id, parent)
    queued = Job(
        institution_id=parent.institution_id,
        programme_revision_id=parent.programme_revision_id,
        kind="ACTION_PLAN",
        payload_json=intent,
        idempotency_key=request.idempotency_key,
        is_synthetic=parent.is_synthetic,
    )
    session.add(queued)
    session.flush()
    run = ActionPlanRun(
        institution_id=parent.institution_id,
        programme_id=parent.programme_id,
        programme_revision_id=parent.programme_revision_id,
        career_run_id=parent.id,
        career_fingerprint=parent.fingerprint,
        job_id=queued.id,
        mode=request.mode,
        request_json=resolved,
        manifest_json=manifest,
        is_synthetic=parent.is_synthetic,
    )
    session.add(run)
    session.flush()
    for row in rows:
        session.add(
            PlanRecommendation(
                plan_run_id=run.id,
                recommendation_id=row.id,
                career_run_id=parent.id,
                programme_revision_id=parent.programme_revision_id,
                recommendation_version=row.version_sha256,
                is_synthetic=parent.is_synthetic,
            )
        )
    session.commit()
    session.refresh(run)
    return run


def get_plan(session, run_id):
    run = session.get(ActionPlanRun, run_id)
    if run is None:
        raise DomainError("NOT_FOUND", "Academic action plan was not found", 404)
    return run


def lock_plan_for_job(session, job_id, settings):
    job = session.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None or job.kind != "ACTION_PLAN":
        raise DomainError("NOT_FOUND", "Action-plan job was not found", 404)
    if job.status != JobStatus.RUNNING:
        _conflict("Action-plan job is not running; historical plans remain immutable")
    run = session.scalar(
        select(ActionPlanRun).where(ActionPlanRun.job_id == job.id).with_for_update()
    )
    if (
        run is None
        or run.result_json
        or (run.institution_id, run.programme_revision_id, run.is_synthetic)
        != (job.institution_id, job.programme_revision_id, job.is_synthetic)
    ):
        _conflict("Action-plan job and frozen snapshot disagree")
    lock_institution(session, run.institution_id)
    if digest(inventory_snapshot(session, run.programme_revision_id)) != run.manifest_json.get(
        "inventory_hash"
    ):
        _conflict("Frozen course inventory changed; submit a new plan")
    allowed, _ = _parent_state(session, run, settings, for_update=True)
    if not allowed:
        _conflict("Parent career findings or reviews changed; submit a new plan")
    return run, job


def source_signatures(session, evidence, *, for_update=False):
    signatures = career.source_signatures(session, evidence, for_update=for_update)
    ids = {
        UUID(str(item["record_id"]))
        for item in evidence
        if item.get("kind") in {"sdg", "sdg_goal", "sdg_target"}
    }
    if ids:
        query = select(SDGReference).where(SDGReference.id.in_(ids)).order_by(SDGReference.id)
        if for_update:
            query = query.with_for_update()
        rows = session.scalars(query.execution_options(populate_existing=True)).all()
        if {row.id for row in rows} != ids:
            _conflict("A frozen SDG reference is unavailable")
        for row in rows:
            values = {
                column.key: getattr(row, column.key) for column in inspect(row).mapper.column_attrs
            }
            signatures[f"sdg:{row.id}"] = digest(
                json.loads(json.dumps(values, default=str, sort_keys=True))
            )
    return signatures


def access_state(session, run, settings, *, for_update=False):
    from shiftos.api.routers.analysis import _access_state

    allowed, limitations = _parent_state(session, run, settings, for_update=for_update)
    if not allowed:
        return False, limitations
    manifest = dict(run.manifest_json)
    pointers = manifest.get("packet", {}).get("references")
    if (
        not isinstance(pointers, list)
        or len(pointers) > 300
        or any(
            not isinstance(item, dict) or type(item.get("is_synthetic")) is not bool
            for item in pointers
        )
    ):
        return False, ["Frozen plan source inventory is unavailable"]
    # Genuine public benchmarks/resources retain their original evidence lane,
    # including when they inform a clearly fictional programme demonstration.
    for synthetic in {item["is_synthetic"] for item in pointers} or {run.is_synthetic}:
        grouped = [
            {**item, "kind": "syllabus"}
            if item.get("kind") in {"curriculum", "curriculum_gap"}
            else item
            for item in pointers
            if item["is_synthetic"] == synthetic
        ]
        facade = SimpleNamespace(
            manifest_json={**manifest, "packet": {"references": grouped}},
            programme_revision_id=run.programme_revision_id,
            is_synthetic=synthetic,
        )
        allowed, limitations = _access_state(session, facade, settings)
        if not allowed:
            return False, limitations
    try:
        if source_signatures(
            session, run.manifest_json["packet"]["references"], for_update=for_update
        ) != run.manifest_json.get("source_signatures"):
            return False, [
                "A plan resource, SDG or source record changed; revalidation is required"
            ]
    except (DomainError, KeyError, TypeError, ValueError):
        return False, ["Plan source identity is unavailable; revalidation is required"]
    return True, []


def plan_history(session, career_run_id, limit=50, offset=0):
    career.get_career(session, career_run_id)
    query = select(ActionPlanRun).where(ActionPlanRun.career_run_id == career_run_id)
    return {
        "items": session.scalars(
            query.order_by(ActionPlanRun.created_at.desc(), ActionPlanRun.id)
            .limit(limit)
            .offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(query.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }


def review_history(session, run_id, limit=50, offset=0):
    get_plan(session, run_id)
    query = select(ActionPlanReview).where(ActionPlanReview.plan_run_id == run_id)
    return {
        "items": session.scalars(
            query.order_by(ActionPlanReview.reviewed_at, ActionPlanReview.id)
            .limit(limit)
            .offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(query.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }


def persist_result(session, run, result, settings):
    from shiftos.schemas.pathways import PlanRequest, PlanResult
    from shiftos.services.pathways.engine import validate_plan_result

    locked, _ = lock_plan_for_job(session, run.job_id, settings)
    if locked.id != run.id:
        _conflict("Action-plan result owner differs from the running job")
    run = locked
    result = PlanResult.model_validate(result)
    validate_plan_result(result)
    if (
        result.programme_id,
        result.programme_revision_id,
        result.career_run_id,
        result.career_fingerprint,
        result.is_synthetic,
    ) != (
        run.programme_id,
        run.programme_revision_id,
        run.career_run_id,
        run.career_fingerprint,
        run.is_synthetic,
    ):
        _conflict("Action-plan result belongs to another parent or programme snapshot")
    if digest(result.career.model_dump(mode="json")) != run.career_fingerprint:
        _conflict("The action plan changes its immutable parent career result")
    expected = {
        UUID(row["id"]): row["version"] for row in run.manifest_json["recommendation_bindings"]
    }
    if (
        len(result.recommendations) != len(expected)
        or {item.id: item.version_sha256 for item in result.recommendations} != expected
    ):
        _conflict("Action-plan recommendations differ from the frozen selected versions")
    if any(
        digest(item.recommendation.model_dump(mode="json")) != expected[item.id]
        for item in result.recommendations
    ):
        _conflict("The action plan changes a frozen parent recommendation")
    if len(result.overview.course_ids) != len(result.career.course_ids) or set(
        result.overview.course_ids
    ) != set(result.career.course_ids):
        _conflict("The action plan does not account for every parent course")
    frozen_request = PlanRequest.model_validate(run.request_json)
    if result.inputs.model_dump(
        mode="json", exclude={"idempotency_key"}
    ) != frozen_request.model_dump(mode="json", exclude={"idempotency_key"}):
        _conflict("The action plan changes its frozen planning inputs")
    output = result.model_dump(mode="json")
    run.result_json, run.fingerprint = output, digest(output)
    run.method_version, run.schema_version = result.method_version, result.schema_version
    usage_fields = {
        "provider",
        "requested_model",
        "actual_model",
        "usage",
        "request_count",
        "observed_cost",
        "status",
        "http_status",
        "duration_ms",
        "error_code",
        "prompt_version",
    }
    run.model_usage_json = {
        key: value for key, value in output["model"].items() if key in usage_fields
    }
    actual = output["model"].get("actual_model")
    run.model_name = actual if isinstance(actual, str) else None
    session.flush()


def append_review(session, run_id, request, settings):
    run = get_plan(session, run_id)
    lock_institution(session, run.institution_id)
    session.refresh(run)
    job = session.get(Job, run.job_id)
    if (
        job is None
        or job.status not in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
        or not run.result_json
    ):
        _conflict("Only completed academic action plans may be reviewed")
    if run.fingerprint != request.expected_plan_fingerprint:
        _conflict("The action-plan fingerprint differs from the reviewed version")
    if request.decision in {"approved", "no_change_required"}:
        allowed, _ = access_state(session, run, settings, for_update=True)
        if not allowed:
            _conflict("Stale or restricted academic plans require revalidation before approval")
    row = ActionPlanReview(
        plan_run_id=run.id,
        programme_revision_id=run.programme_revision_id,
        plan_fingerprint=run.fingerprint,
        actor="authenticated_analysis_operator",
        decision=request.decision,
        reason=request.reason,
        reviewed_at=datetime.now(UTC),
        is_synthetic=run.is_synthetic,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
