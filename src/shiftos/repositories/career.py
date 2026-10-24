"""Queue frozen career requests, preserve results and append human decisions."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid5

from sqlalchemy import func, inspect, select

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import (
    AcademicStandard,
    AIImpactEvidence,
    CareerRecommendation,
    CareerReview,
    CareerRun,
    DatasetVersion,
    Document,
    DocumentAnchor,
    EvidenceReference,
    Job,
    Occupation,
    OccupationalTask,
    OccupationSkill,
    Programme,
    ProgrammeRevision,
    Skill,
    Source,
    WorkforceObservation,
)
from shiftos.repositories.analysis import inventory_snapshot
from shiftos.repositories.catalogue import digest, lock_institution
from shiftos.schemas.career import CareerRequest, CareerResult, ReviewRequest
from shiftos.services.academic import require_programme


def enqueue_career(session, programme_id: UUID, request: CareerRequest) -> CareerRun:
    programme = require_programme(session, programme_id)
    institution = lock_institution(session, programme.institution_id)
    session.refresh(programme)
    intent = {
        "programme_id": str(programme.id),
        "request": request.model_dump(mode="json", exclude={"idempotency_key"}),
    }
    if request.idempotency_key:
        job = session.scalar(
            select(Job).where(
                Job.institution_id == institution.id,
                Job.kind == "CAREER_ANALYSIS",
                Job.idempotency_key == request.idempotency_key,
            )
        )
        if job:
            if job.payload_json != intent:
                raise DomainError(
                    "CONFLICT", "Career idempotency key has different request content", 409
                )
            run = session.scalar(select(CareerRun).where(CareerRun.job_id == job.id))
            if run is None:
                raise DomainError(
                    "CONFLICT", "Career job has no run; administrator review required", 409
                )
            return run
    revision_id = request.revision_id or programme.active_revision_id
    revision = session.get(ProgrammeRevision, revision_id) if revision_id else None
    if revision is None or revision.programme_id != programme.id:
        raise DomainError("NOT_FOUND", "Selected programme revision was not found", 404)
    inventory = inventory_snapshot(session, revision.id)
    if not inventory:
        raise DomainError(
            "CONFLICT", "Import a nonempty course inventory before career analysis", 409
        )
    if not (institution.is_synthetic == programme.is_synthetic == revision.is_synthetic) or any(
        row["is_synthetic"] != programme.is_synthetic for row in inventory
    ):
        raise DomainError("CONFLICT", "Career snapshot has inconsistent synthetic lineage", 409)
    cutoff = request.as_of or datetime.now(UTC)
    resolved = request.model_dump(mode="json", exclude={"idempotency_key"})
    resolved.update(revision_id=str(revision.id), as_of=cutoff.isoformat())
    job = Job(
        institution_id=institution.id,
        programme_revision_id=revision.id,
        kind="CAREER_ANALYSIS",
        payload_json=intent,
        idempotency_key=request.idempotency_key,
        is_synthetic=programme.is_synthetic,
    )
    session.add(job)
    session.flush()
    run = CareerRun(
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


def get_career(session, run_id: UUID) -> CareerRun:
    run = session.get(CareerRun, run_id)
    if run is None:
        raise DomainError("NOT_FOUND", "Career analysis was not found", 404)
    return run


def lock_career_for_job(session, job_id: UUID) -> tuple[CareerRun, Job]:
    job = session.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None or job.kind != "CAREER_ANALYSIS":
        raise DomainError("NOT_FOUND", "Career job was not found", 404)
    if job.status != JobStatus.RUNNING:
        raise DomainError(
            "CONFLICT", "Career job is not running; historical results are immutable", 409
        )
    run = session.scalar(select(CareerRun).where(CareerRun.job_id == job.id).with_for_update())
    if run is None or (run.programme_revision_id, run.institution_id, run.is_synthetic) != (
        job.programme_revision_id,
        job.institution_id,
        job.is_synthetic,
    ):
        raise DomainError("CONFLICT", "Career job and snapshot ownership disagree", 409)
    if run.result_json:
        raise DomainError("CONFLICT", "Career results are immutable; submit a new run", 409)
    if digest(inventory_snapshot(session, run.programme_revision_id)) != run.manifest_json.get(
        "inventory_hash"
    ):
        raise DomainError("CONFLICT", "Frozen course inventory changed; submit a new run", 409)
    return run, job


RECORD_MODELS = {
    "academic_standard": AcademicStandard,
    "occupation": Occupation,
    "skill": Skill,
    "occupation_skill": OccupationSkill,
    "task": OccupationalTask,
    "ai_evidence": AIImpactEvidence,
    "workforce": WorkforceObservation,
}


def source_signatures(session, evidence: list[dict], *, for_update=False) -> dict[str, str]:
    """Bounded bulk hashes preserve provenance without another restricted text copy."""
    if not isinstance(evidence, list) or len(evidence) > 300:
        raise DomainError("CONFLICT", "Invalid frozen career evidence inventory", 409)
    models = {
        "source": Source,
        "anchor": DocumentAnchor,
        "document": Document,
        "reference": EvidenceReference,
        "version": DatasetVersion,
        **RECORD_MODELS,
    }
    identities = {label: set() for label in models}
    try:
        for pointer in evidence:
            identities["source"].add(UUID(str(pointer["source_id"])))
            reference_id = UUID(str(pointer["evidence_reference_id"]))
            if pointer.get("kind") in {"syllabus", "curriculum", "curriculum_gap"}:
                identities["anchor"].add(reference_id)
            else:
                identities["reference"].add(reference_id)
                identities["version"].add(UUID(str(pointer["version_id"])))
                if pointer.get("kind") in RECORD_MODELS:
                    identities[pointer["kind"]].add(UUID(str(pointer["record_id"])))
        signatures = {}
        for label, model in models.items():
            wanted = identities[label]
            if not wanted:
                continue
            query = select(model).where(model.id.in_(wanted)).order_by(model.id)
            if for_update:
                query = query.with_for_update()
            rows = session.scalars(query.execution_options(populate_existing=True)).all()
            if {row.id for row in rows} != wanted:
                raise ValueError
            if label == "anchor":
                identities["document"].update(row.document_id for row in rows)
            for row in rows:
                values = {
                    column.key: getattr(row, column.key)
                    for column in inspect(row).mapper.column_attrs
                }
                signatures[f"{label}:{row.id}"] = digest(
                    json.loads(json.dumps(values, default=str, sort_keys=True))
                )
    except (KeyError, TypeError, ValueError):
        raise DomainError(
            "CONFLICT", "Career evidence identity changed; revalidation is required", 409
        ) from None
    return signatures


def access_state(session, run: CareerRun, settings, *, for_update=False) -> tuple[bool, list[str]]:
    """Revalidate policy, source status/content and frozen curriculum on every read/review."""
    from shiftos.api.routers.analysis import _access_state

    programme = session.get(Programme, run.programme_id)
    if programme is None or programme.active_revision_id != run.programme_revision_id:
        return False, ["Programme active revision changed; revalidation is required"]
    if digest(inventory_snapshot(session, run.programme_revision_id)) != run.manifest_json.get(
        "inventory_hash"
    ):
        return False, ["Frozen course inventory changed; revalidation is required"]
    # The existing source guard distinguishes document anchors from dataset versions.
    # Preserve Phase 5 evidence kinds in storage and normalize only this guard's view.
    manifest = dict(run.manifest_json)
    packet = manifest.get("packet")
    if isinstance(packet, dict) and isinstance(packet.get("references"), list):
        manifest["packet"] = {
            **packet,
            "references": [
                {**pointer, "kind": "syllabus"}
                if isinstance(pointer, dict)
                and pointer.get("kind") in {"curriculum", "curriculum_gap"}
                else pointer
                for pointer in packet["references"]
            ],
        }
    facade = SimpleNamespace(
        manifest_json=manifest,
        programme_revision_id=run.programme_revision_id,
        is_synthetic=run.is_synthetic,
    )
    allowed, limitations = _access_state(session, facade, settings)
    if not allowed:
        return False, limitations
    pointers = run.manifest_json.get("packet", {}).get("references", [])
    try:
        if source_signatures(session, pointers, for_update=for_update) != run.manifest_json.get(
            "source_signatures"
        ):
            return False, ["Source content or provenance changed; revalidation is required"]
    except DomainError:
        return False, ["Source identity is unavailable; revalidation is required"]
    return True, []


def persist_result(session, run: CareerRun, result: CareerResult) -> None:
    from shiftos.services.career.engine import validate_career_result

    locked, _ = lock_career_for_job(session, run.job_id)
    if locked.id != run.id:
        raise DomainError("CONFLICT", "Career result owner does not match the running job", 409)
    run = locked
    result = CareerResult.model_validate(result)
    validate_career_result(result)
    if (
        result.programme_id != run.programme_id
        or result.programme_revision_id != run.programme_revision_id
        or result.is_synthetic != run.is_synthetic
    ):
        raise DomainError("CONFLICT", "Career result belongs to another snapshot", 409)
    expected = {str(row["id"]) for row in run.manifest_json["inventory"]}
    if (
        len(result.course_ids) != len(expected)
        or {str(value) for value in result.course_ids} != expected
    ):
        raise DomainError("CONFLICT", "Career result must account for every frozen course", 409)
    keys = [item.key for item in result.recommendations]
    if len(keys) != len(set(keys)) or any(
        item.programme_revision_id != run.programme_revision_id
        or not set(map(str, item.course_ids)) <= expected
        for item in result.recommendations
    ):
        raise DomainError(
            "CONFLICT", "Career recommendations must belong to this frozen snapshot", 409
        )
    output = result.model_dump(mode="json")
    for item in output["recommendations"]:
        session.add(
            CareerRecommendation(
                id=uuid5(run.id, item["key"]),
                run_id=run.id,
                programme_revision_id=run.programme_revision_id,
                recommendation_key=item["key"],
                version_sha256=digest(item),
                result_json=item,
                is_synthetic=run.is_synthetic,
            )
        )
    run.result_json, run.fingerprint = output, digest(output)
    run.method_version, run.schema_version = result.method_version, result.schema_version
    # Detailed model choices contain evidence quotations and belong only in the
    # rights-controlled immutable result, never in operational usage metadata.
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


def career_history(session, programme_id, limit=50, offset=0):
    require_programme(session, programme_id)
    query = select(CareerRun).where(CareerRun.programme_id == programme_id)
    return {
        "items": session.scalars(
            query.order_by(CareerRun.created_at.desc(), CareerRun.id).limit(limit).offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(query.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }


def recommendations(session, run_id, limit=50, offset=0):
    get_career(session, run_id)
    query = select(CareerRecommendation).where(CareerRecommendation.run_id == run_id)
    return {
        "items": session.scalars(
            query.order_by(CareerRecommendation.recommendation_key).limit(limit).offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(query.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }


def get_recommendation(session, recommendation_id):
    row = session.get(CareerRecommendation, recommendation_id)
    if row is None:
        raise DomainError("NOT_FOUND", "Career recommendation was not found", 404)
    return row


def append_review(session, recommendation_id, request: ReviewRequest, settings):
    recommendation = get_recommendation(session, recommendation_id)
    run = get_career(session, recommendation.run_id)
    # Serialize reviews with catalogue revision changes through the established institution lock.
    lock_institution(session, run.institution_id)
    session.refresh(recommendation)
    if recommendation.version_sha256 != request.expected_recommendation_version:
        raise DomainError(
            "CONFLICT", "Recommendation version differs from the reviewed version", 409
        )
    job = session.get(Job, run.job_id)
    if (
        job is None
        or job.status not in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
        or not run.result_json
    ):
        raise DomainError("CONFLICT", "Only completed career recommendations may be reviewed", 409)
    if request.decision in {"approved", "no_change_required"}:
        allowed, _ = access_state(session, run, settings, for_update=True)
        if not allowed:
            raise DomainError(
                "CONFLICT",
                "Stale or restricted recommendations require a new analysis before approval",
                409,
            )
    row = CareerReview(
        recommendation_id=recommendation.id,
        run_id=run.id,
        programme_revision_id=run.programme_revision_id,
        recommendation_version=recommendation.version_sha256,
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


def review_history(session, recommendation_id, limit=50, offset=0):
    get_recommendation(session, recommendation_id)
    query = select(CareerReview).where(CareerReview.recommendation_id == recommendation_id)
    return {
        "items": session.scalars(
            query.order_by(CareerReview.reviewed_at, CareerReview.id).limit(limit).offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(query.subquery())) or 0,
        "limit": limit,
        "offset": offset,
    }
