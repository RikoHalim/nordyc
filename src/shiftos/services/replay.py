"""Read-only explicit dependency assessment using the existing current-source gates."""

from uuid import UUID

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import (
    ActionPlanRun,
    AnalysisRun,
    CareerRecommendation,
    CareerReview,
    CareerRun,
    DatasetVersion,
    Document,
    DocumentAnchor,
    EvidenceReference,
    Job,
    OccupationSkill,
    Programme,
    ProgrammeRevision,
    Source,
    WorkforceObservation,
)
from shiftos.repositories import career, pathways
from shiftos.schemas.pathways import PlanResult
from shiftos.schemas.replay import (
    ReplayAction,
    ReplayAssessment,
    ReplayEligibility,
    ReplayImpact,
    ReplayRequest,
)

ANCHORS = {"curriculum", "curriculum_gap", "syllabus"}


def _missing():
    raise DomainError("NOT_FOUND", "Requested programme-scoped replay record was not found", 404)


def _owned(session, model, identity, programme_id):
    row = session.get(model, UUID(str(identity)))
    if row is None or row.programme_id != programme_id:
        _missing()
    return row


def _pointers(run):
    return run.manifest_json.get("packet", {}).get("references", [])


def _matches(pointer, kind, identity):
    expected = str(identity)
    if kind == "source":
        field = "source_id"
    elif kind == "dataset_version":
        if pointer.get("kind") in ANCHORS:
            return False
        field = "version_id"
    elif kind == "evidence_reference":
        if pointer.get("kind") in ANCHORS:
            return False
        field = "evidence_reference_id"
    elif kind == "document_anchor":
        if pointer.get("kind") not in ANCHORS:
            return False
        field = "record_id"
    else:
        required = {
            "occupation_requirement": "occupation_skill",
            "workforce_observation": "workforce",
        }
        if pointer.get("kind") != required.get(kind):
            return False
        field = "record_id"
    return str(pointer.get(field)) == expected


def _change_record(session, change, programme_id, career_run):
    if change.kind == "assumption":
        return None
    if change.kind == "programme_revision":
        return _owned(session, ProgrammeRevision, change.id, programme_id)
    if change.kind == "career_review":
        row = session.get(CareerReview, change.id)
        recommendation = session.get(CareerRecommendation, row.recommendation_id) if row else None
        if recommendation is None or career_run is None or recommendation.run_id != career_run.id:
            _missing()
        return row
    models = {
        "source": Source,
        "dataset_version": DatasetVersion,
        "evidence_reference": EvidenceReference,
        "document_anchor": DocumentAnchor,
        "occupation_requirement": OccupationSkill,
        "workforce_observation": WorkforceObservation,
    }
    row = session.get(models[change.kind], change.id)
    if row is None:
        _missing()
    if change.kind == "document_anchor":
        document = session.get(Document, row.document_id)
        revision = (
            session.get(ProgrammeRevision, document.programme_revision_id) if document else None
        )
        if revision is None or revision.programme_id != programme_id:
            _missing()
    return row


def assess_replay(session, programme_id, request: ReplayRequest, settings) -> ReplayAssessment:
    """Classify explicit changes. Never execute a job or reinterpret prior approval."""
    from shiftos.api.routers.analysis import _access_state

    programme = session.get(Programme, programme_id)
    if programme is None:
        _missing()
    plan = (
        _owned(session, ActionPlanRun, request.plan_run_id, programme_id)
        if request.plan_run_id
        else None
    )
    career_id = request.career_run_id or (plan.career_run_id if plan else None)
    career_run = _owned(session, CareerRun, career_id, programme_id) if career_id else None
    if plan and (
        career_run.id != plan.career_run_id
        or career_run.programme_revision_id != plan.programme_revision_id
    ):
        raise DomainError("CONFLICT", "Replay snapshots do not share exact parent lineage", 409)
    linked = plan.manifest_json.get("phase4_parent", {}).get("id") if plan else None
    analysis_id = request.analysis_id or linked
    analysis = _owned(session, AnalysisRun, analysis_id, programme_id) if analysis_id else None
    if (
        analysis
        and career_run
        and analysis.programme_revision_id != career_run.programme_revision_id
    ):
        raise DomainError(
            "CONFLICT", "Replay snapshots belong to different curriculum revisions", 409
        )
    if request.analysis_id and linked and str(request.analysis_id) != str(linked):
        raise DomainError("CONFLICT", "Replay plan links another exact Phase 4 snapshot", 409)
    runs = {
        key: value
        for key, value in {"phase4": analysis, "phase5": career_run, "phase6": plan}.items()
        if value
    }
    eligibility = []
    for phase, run in runs.items():
        job = session.get(Job, run.job_id)
        completed = job is not None and job.status in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
        allowed = False
        if completed:
            guard = {
                "phase4": _access_state,
                "phase5": career.access_state,
                "phase6": pathways.access_state,
            }[phase]
            allowed, _ = guard(session, run, settings)
        eligibility.append(
            ReplayEligibility(
                phase=phase,
                run_id=run.id,
                current_eligible=allowed,
                reason_code="CURRENT"
                if allowed
                else "REVALIDATION_REQUIRED"
                if completed
                else "NOT_COMPLETED",
            )
        )
    current = {row.phase: row.current_eligible for row in eligibility}
    # Inspect frozen structured lineage only. Source prose is never returned.
    result = PlanResult.model_validate(plan.result_json) if plan and plan.result_json else None
    all_keys = [row.key for row in result.pathways] if result else []
    required = {phase for phase, allowed in current.items() if not allowed}
    impacts = []
    for change in request.changes:
        row = _change_record(session, change, programme_id, career_run)
        affected, keys = set(), []
        classification, reason = (
            "needs_applicability_review",
            "UNFROZEN_INPUT_REQUIRES_APPLICABILITY_REVIEW",
        )
        if change.kind == "programme_revision":
            if all(run.programme_revision_id == row.id for run in runs.values()) and all(
                current.values()
            ):
                classification, reason = "no_effect", "EXACT_CURRENT_REVISION_ALREADY_SELECTED"
            else:
                affected = {"phase4", "phase5", "phase6"}
                classification, reason = (
                    "entire_plan_affected",
                    "CURRICULUM_REVISION_REQUIRES_NEW_LINEAGE",
                )
                keys = all_keys
        elif change.kind == "assumption":
            if result is None:
                raise DomainError(
                    "CONFLICT", "Select a completed action plan to compare assumptions", 409
                )
            same = any(item == change.assumption for item in result.inputs.scenarios)
            if same:
                classification, reason = "no_effect", "EXACT_FROZEN_ASSUMPTION_UNCHANGED"
            else:
                affected, keys = {"phase6"}, all_keys
                classification, reason = (
                    "entire_plan_affected",
                    "EXPLICIT_ASSUMPTION_RECOMPARISON_REQUIRED",
                )
        elif change.kind == "career_review":
            selected = {item.id for item in result.recommendations} if result else set()
            affected = {"phase6"}
            keys = (
                [
                    item.key
                    for item in result.pathways
                    if item.recommendation_id == row.recommendation_id
                ]
                if result
                else []
            )
            classification, reason = (
                "pathway_affected" if keys else "entire_plan_affected",
                "REVIEW_REQUIRES_EXACT_VERSION_ELIGIBILITY_RECHECK",
            )
            if result and row.recommendation_id not in selected:
                affected = set()
                classification, reason = "no_effect", "REVIEW_OUTSIDE_SELECTED_RECOMMENDATIONS"
        else:
            for phase, run in runs.items():
                if any(_matches(pointer, change.kind, change.id) for pointer in _pointers(run)):
                    affected.add(phase)
            if "phase4" in affected:
                affected.update({"phase5", "phase6"})
            elif "phase5" in affected:
                affected.add("phase6")
            if affected:
                changed_ids = (
                    {
                        pointer.get("id")
                        for pointer in _pointers(plan)
                        if _matches(pointer, change.kind, change.id)
                    }
                    if plan
                    else set()
                )
                keys = (
                    [
                        item.key
                        for item in result.pathways
                        if any(c.reference_id in changed_ids for c in item.citations)
                    ]
                    if result
                    else []
                )
                classification = (
                    "pathway_affected"
                    if keys and set(keys) != set(all_keys)
                    else "entire_plan_affected"
                    if plan
                    else "new_analysis_required"
                )
                reason = "FROZEN_DEPENDENCY_REVALIDATION_REQUIRED"
            elif change.kind in {
                "workforce_observation",
                "occupation_requirement",
                "source",
                "dataset_version",
                "evidence_reference",
                "document_anchor",
            }:
                # Not being in an old packet proves no irrelevance. Retrieval must
                # reassess newly admitted evidence before it can affect decisions.
                affected = {"phase4", "phase5", "phase6"}
        required.update(affected)
        impacts.append(
            ReplayImpact(
                kind=change.kind,
                id=change.id,
                classification=classification,
                eligibility_invalidated=any(not current.get(phase, True) for phase in affected),
                affected_phases=sorted(affected),
                affected_pathway_keys=keys,
                reason_code=reason,
            )
        )
    actions = [
        ReplayAction(
            phase=phase,
            action={
                "phase4": "submit_new_analysis",
                "phase5": "submit_new_career_assessment",
                "phase6": "submit_new_action_plan",
            }[phase],
        )
        for phase in sorted(required)
    ]
    return ReplayAssessment(
        programme_id=programme.id,
        active_revision_id=programme.active_revision_id,
        eligibility=eligibility,
        impacts=impacts,
        actions=actions,
        limitations=[
            "Explicit preflight only; no jobs, provider calls, permissions or records are changed.",
            "Unfrozen evidence needs retrieval/applicability review; absence is not no effect.",
            "Results remain historical; prior approvals never authorise a new analysis version.",
        ],
    )
