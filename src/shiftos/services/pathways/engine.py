"""Build source-bounded proposals from exact immutable Phase 5 recommendations.

Procedural review dependencies describe a proposed academic decision process.
They never invent subject prerequisites, taught outcomes, completed learning or
graduate competence. All external acquisition and model calls remain elsewhere.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import (
    AnalysisRun,
    CareerRecommendation,
    CareerReview,
    CareerRun,
    CourseFinding,
    Institution,
    Job,
    Programme,
    ProgrammeRevision,
    Skill,
)
from shiftos.repositories.career import access_state
from shiftos.repositories.catalogue import digest
from shiftos.schemas.career import CareerResult
from shiftos.schemas.pathways import (
    AcademicPathway,
    DurationEstimate,
    PathwayPrerequisite,
    PathwayStep,
    PlanRequest,
    PlanResult,
    ProgrammeOverview,
    RecommendationSnapshot,
)
from shiftos.services.career.engine import validate_career_result
from shiftos.services.pathways.scenarios import build_scenarios


def _invalid(message):
    raise DomainError("PLAN_INPUT_INVALID", message, 422)


def _validate_dependency_graph(entries):
    """Check explicit procedural edges, without inventing subject prerequisites.

    Each entry is ``(stable_key, ordinal, dependency_keys)``. The displayed order
    must respect the acyclic graph, while unrelated steps need not depend on one
    another merely because one happens to be displayed first.
    """
    keys = [key for key, _, _ in entries]
    ordinals = [ordinal for _, ordinal, _ in entries]
    if len(set(keys)) != len(keys) or len(set(ordinals)) != len(ordinals):
        _invalid("Pathway step identities and ordinals must be unique")
    if any(type(ordinal) is not int or ordinal < 1 for ordinal in ordinals):
        _invalid("Pathway step ordinals must be positive integers")
    order = dict(zip(keys, ordinals, strict=True))
    pending = {}
    for key, _, dependencies in entries:
        dependencies = list(dependencies)
        if len(dependencies) != len(set(dependencies)) or not set(dependencies) <= set(keys):
            _invalid("A pathway dependency is duplicated or outside its pathway")
        if key in dependencies:
            _invalid("A pathway step cannot depend on itself")
        pending[key] = set(dependencies)
    visited = set()
    while pending:
        ready = {key for key, dependencies in pending.items() if dependencies <= visited}
        if not ready:
            _invalid("Pathway dependencies contain a cycle")
        visited.update(ready)
        pending = {key: dependencies for key, dependencies in pending.items() if key not in ready}
    if any(
        order[dependency] >= ordinal
        for _, ordinal, dependencies in entries
        for dependency in dependencies
    ):
        _invalid("Displayed pathway order contradicts its explicit dependencies")


def _load_parent(session, career_run_id, settings, as_of):
    if as_of.tzinfo is None or as_of > datetime.now(UTC) + timedelta(seconds=1):
        _invalid("Plan evidence cutoff must be aware and cannot be in the future")
    run = session.get(CareerRun, career_run_id)
    if run is None:
        raise DomainError("NOT_FOUND", "Parent career analysis was not found", 404)
    job = session.get(Job, run.job_id)
    if (
        job is None
        or job.status not in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
        or not run.result_json
    ):
        raise DomainError("CONFLICT", "Complete the parent career analysis before planning", 409)
    allowed, _ = access_state(session, run, settings)
    if not allowed:
        raise DomainError("CONFLICT", "Parent career sources or revision require revalidation", 409)
    career = validate_career_result(CareerResult.model_validate(run.result_json))
    if (
        run.fingerprint != digest(run.result_json)
        or career.programme_id != run.programme_id
        or career.programme_revision_id != run.programme_revision_id
        or career.is_synthetic != run.is_synthetic
        or career.as_of > as_of
    ):
        _invalid("Parent career snapshot identity or evidence cutoff does not agree")
    rows = session.scalars(
        select(CareerRecommendation)
        .where(CareerRecommendation.run_id == run.id)
        .order_by(CareerRecommendation.recommendation_key)
    ).all()
    expected = {value.key: value for value in career.recommendations}
    if len(rows) != len(expected) or {row.recommendation_key for row in rows} != set(expected):
        _invalid("Parent career recommendation inventory is incomplete")
    for row in rows:
        value = expected[row.recommendation_key].model_dump(mode="json")
        if (
            row.programme_revision_id != run.programme_revision_id
            or row.is_synthetic != run.is_synthetic
            or row.version_sha256 != digest(value)
            or row.result_json != value
        ):
            _invalid("Parent recommendation content, version or revision does not agree")
    reviews = session.scalars(
        select(CareerReview)
        .where(CareerReview.run_id == run.id, CareerReview.reviewed_at <= as_of)
        .order_by(CareerReview.reviewed_at, CareerReview.id)
    ).all()
    latest, history = {}, []
    row_ids = {row.id: row for row in rows}
    for review in reviews:
        recommendation = row_ids.get(review.recommendation_id)
        if (
            recommendation is None
            or review.recommendation_version != recommendation.version_sha256
            or review.programme_revision_id != run.programme_revision_id
            or review.is_synthetic != run.is_synthetic
        ):
            _invalid("Parent review belongs to a different recommendation or revision")
        latest[recommendation.id] = review
        history.append(review)
    return run, career, rows, latest, history


def _normal(value):
    return " ".join(value.split())


def _check_citations(citations, evidence):
    for citation in citations:
        item = evidence.get(citation.reference_id)
        if (
            item is None
            or not item.internal_eligible
            or not item.rights.internal_analysis_allowed
            or not item.rights.excerpt_output_allowed
            or item.review_status == "rejected"
            or not _normal(citation.quote)
            or _normal(citation.quote) not in _normal(item.excerpt)
        ):
            _invalid("Plan citation does not match admitted permitted evidence")


def _consideration(recommendation, reviews):
    decision = reviews[-1]["decision"] if reviews else None
    if decision == "rejected":
        return "rejected"
    if recommendation.category == "no_change" or decision == "no_change_required":
        return "no_change"
    return "eligible" if decision in {"under_review", "approved"} else "needs_review"


def _snapshots(rows, career, history, selected, as_of):
    wanted = set(selected) or {row.id for row in rows}
    if not wanted <= {row.id for row in rows}:
        _invalid("A selected recommendation belongs to another career analysis")
    recommendations = {row.key: row for row in career.recommendations}
    snapshots = []
    for row in rows:
        if row.id not in wanted:
            continue
        reviews = [
            {
                "id": str(review.id),
                "recommendation_id": str(review.recommendation_id),
                "recommendation_version": review.recommendation_version,
                "decision": review.decision,
                "reason": review.reason,
                "actor": review.actor,
                "reviewed_at": review.reviewed_at.isoformat(),
            }
            for review in history
            if review.recommendation_id == row.id and review.reviewed_at <= as_of
        ]
        recommendation = recommendations[row.recommendation_key]
        snapshots.append(
            RecommendationSnapshot(
                id=row.id,
                version_sha256=row.version_sha256,
                recommendation=recommendation,
                reviews=reviews,
                consideration_status=_consideration(recommendation, reviews),
            )
        )
    return snapshots


def _prerequisites(skill_id, bindings, evidence, as_of):
    from shiftos.schemas.career import CareerCitation

    prerequisites = []
    for binding in bindings:
        if binding.target_skill_id != skill_id:
            continue
        if binding.target_skill_id == binding.prerequisite_skill_id:
            _invalid("A competency cannot be its own prerequisite")
        citation = CareerCitation(reference_id=binding.reference_id, quote=binding.quote)
        _check_citations([citation], evidence)
        item = evidence[binding.reference_id]
        metadata = item.facts.get("learning_resource", item.facts)
        supported = (
            binding.reviewed
            and binding.reviewed_at <= as_of
            and item.review_status == "reviewed"
            and not item.historical_context_only
            and str(skill_id) in metadata.get("related_skill_ids", [])
            and str(binding.prerequisite_skill_id) in metadata.get("prerequisite_skill_ids", [])
        )
        prerequisites.append(
            PathwayPrerequisite(
                skill_id=binding.prerequisite_skill_id,
                basis=binding.basis,
                citations=[citation] if supported else [],
                status="source_supported" if supported else "needs_review",
            )
        )
    return prerequisites


def _step_specs(academic):
    common = [
        (
            "review",
            "curriculum_review" if academic else "evidence_review",
            [],
            "Inspect the current reviewed learning outcomes and occupational requirement.",
            "Proposed review: identify what the admitted passages establish "
            "and what remains unknown.",
            "Academic reviewers inspect the linked evidence and preserve foundational learning.",
        ),
        (
            "investigate",
            "evidence_review",
            ["review"],
            "Check the existing assessment opportunity and documentation "
            "before proposing training.",
            "Proposed review: distinguish documented intent, assessed evidence "
            "and unknown coverage.",
            "Inspect the relevant assignment or syllabus; obtain missing evidence "
            "rather than infer content from titles.",
        ),
    ]
    if academic:
        common.extend(
            [
                (
                    "practice",
                    "proposed_practice",
                    ["investigate"],
                    "Consider the smallest appropriate practical activity "
                    "only if academic review confirms need.",
                    "Proposed learning objective: practise the cited competency "
                    "in a bounded assessed setting.",
                    "Conditionally propose an existing-course exercise or small applied "
                    "project; no technology, provider or partner is mandated.",
                ),
                (
                    "assess",
                    "assessment_design",
                    ["practice"],
                    "Define observable criteria for the proposed competency and its actual scope.",
                    "Proposed assessment objective: specify the evidence "
                    "a suitable practical task would need to produce.",
                    "Academic staff propose criteria, review validity "
                    "and distinguish participation from demonstrated performance.",
                ),
            ]
        )
    common.append(
        (
            "academic_review",
            "academic_review",
            ["assess" if academic else "investigate"],
            "Record the academic decision, conditions, alternatives "
            "and legitimate no-change outcome.",
            "Proposed review objective: decide whether any intervention "
            "is justified by the evidence.",
            "Submit the proposal to the institution's academic review process; "
            "this system records no automatic implementation approval.",
        )
    )
    return common


def _pathways(snapshots, resources, evidence, inputs, as_of, revision_id):
    from shiftos.services.pathways.resources import duration_for

    references = {item.id: item for item in evidence}
    selected = {row.id for row in snapshots}
    if any(binding.recommendation_id not in selected for binding in inputs.durations):
        _invalid("A duration binding targets an unselected recommendation")
    if any(
        binding.step_key not in {"review", "investigate", "practice", "assess", "academic_review"}
        for binding in inputs.durations
    ):
        _invalid("A duration binding targets an unknown step identity")
    all_bindings = {}
    for binding in inputs.prerequisites:
        if binding.target_skill_id not in {
            row.recommendation.skill_id for row in snapshots if row.recommendation.skill_id
        }:
            _invalid("A prerequisite targets an unselected competency")
        all_bindings.setdefault(binding.target_skill_id, set()).add(binding.prerequisite_skill_id)
    # A skill prerequisite is distinct from a procedural review dependency.
    nodes = set(all_bindings) | {value for values in all_bindings.values() for value in values}
    pending = {node: set(all_bindings.get(node, [])) for node in nodes}
    while pending:
        roots = {node for node, dependencies in pending.items() if not dependencies}
        if not roots:
            _invalid("Source prerequisite assertions contain a cycle")
        pending = {
            node: dependencies - roots
            for node, dependencies in pending.items()
            if node not in roots
        }
    output, used_durations = [], set()
    for snapshot in snapshots:
        recommendation = snapshot.recommendation
        if snapshot.consideration_status in {"no_change", "rejected"}:
            continue
        academic = (
            snapshot.consideration_status == "eligible"
            and recommendation.evidence_sufficiency != "insufficient_evidence"
            and recommendation.category != "request_review"
        )
        if not academic and recommendation.category != "request_review":
            continue
        attached = [
            resource for resource in resources if resource.skill_id == recommendation.skill_id
        ]
        specs, steps = _step_specs(academic), []
        for position, (key, kind, dependencies, purpose, objective, activity) in enumerate(
            specs, 1
        ):
            binding = next(
                (
                    item
                    for item in inputs.durations
                    if item.recommendation_id == snapshot.id and item.step_key == key
                ),
                None,
            )
            duration = duration_for(binding, evidence, as_of) if binding else DurationEstimate()
            resource_keys = (
                [row.key for row in attached] if key in {"practice", "assess"} and academic else []
            )
            if binding:
                used_durations.add((snapshot.id, key))
                if binding.basis_type == "source" and binding.reference_id not in {
                    row.reference_id for row in attached if row.key in resource_keys
                }:
                    _invalid("Source-based duration is not linked to this step's admitted resource")
            citations = list(recommendation.citations)
            citations.extend(
                citation
                for row in attached
                if row.key in resource_keys
                for citation in row.citations
            )
            citations = list({(row.reference_id, row.quote): row for row in citations}.values())
            steps.append(
                PathwayStep(
                    key=key,
                    position=position,
                    purpose=purpose,
                    objective=objective,
                    activity=activity,
                    step_type=kind,
                    depends_on=dependencies,
                    ordering_basis="procedural_review",
                    proposed_assessment=(
                        "Proposed only: an appropriate assessed task and stated criteria would be "
                        "needed before any bounded demonstration claim. Attendance, enrolment, "
                        "completion, seminars and talks do not establish technical competency."
                    ),
                    resource_keys=resource_keys,
                    duration=duration,
                    citations=citations,
                    conditions=[
                        "Resolve missing or contradictory curriculum evidence "
                        "before implementation.",
                        "All objectives and activities are future proposals, "
                        "not existing taught outcomes.",
                        "Procedural review order does not assert a subject prerequisite "
                        "or calendar schedule.",
                    ],
                )
            )
        _validate_dependency_graph([(row.key, row.position, row.depends_on) for row in steps])
        known = sum(
            (row.duration.hours for row in steps if row.duration.hours is not None), Decimal("0")
        )
        unknown = sum(row.duration.hours is None for row in steps)
        prerequisites = _prerequisites(
            recommendation.skill_id, inputs.prerequisites, references, as_of
        )
        limitations = [
            "No student performance, graduate mastery or existing taught outcome is asserted.",
            "Unknown prerequisites, resources, cost, staff availability "
            "and calendar time stay unknown.",
            "Operator consideration is not a named academic identity or institutional approval.",
        ]
        if not attached:
            limitations.append(
                "No suitable original resource is admitted; verify resources before delivery."
            )
        dependencies = [f"recommendation:{snapshot.id}:{snapshot.version_sha256}"]
        dependencies.extend(
            f"evidence:{citation.reference_id}" for citation in recommendation.citations
        )
        output.append(
            AcademicPathway(
                key=f"path-{recommendation.key}",
                programme_revision_id=revision_id,
                recommendation_id=snapshot.id,
                recommendation_version=snapshot.version_sha256,
                skill_id=recommendation.skill_id,
                occupation_ids=recommendation.occupation_ids,
                pathway_type="academic_intervention" if academic else "evidence_review",
                objective=recommendation.competency_objective,
                steps=steps,
                prerequisites=prerequisites,
                total_hours=None if unknown else known,
                known_hours=known,
                unknown_duration_steps=unknown,
                duration_basis=(
                    "Sum of separately identified learning/contact/assessment "
                    "components where known. Unknown steps prevent a total; "
                    "effort hours are not calendar duration or a completion guarantee."
                ),
                evidence_sufficiency=recommendation.evidence_sufficiency,
                alternatives=[row.model_dump(mode="json") for row in recommendation.alternatives],
                no_change_option=recommendation.no_change_option.model_dump(mode="json"),
                citations=recommendation.citations,
                dependencies=list(dict.fromkeys(dependencies)),
                limitations=limitations,
                review_status="proposed" if academic else "needs_evidence",
            )
        )
    if used_durations != {(row.recommendation_id, row.step_key) for row in inputs.durations}:
        _invalid("A duration targets a nonexistent or ineligible pathway step")
    # Reusing the same provider time for multiple steps would double-count that source claim.
    source_bases = [
        (row.reference_id, row.component)
        for row in inputs.durations
        if row.basis_type == "source" and (row.recommendation_id, row.step_key) in used_durations
    ]
    if len(source_bases) != len(set(source_bases)):
        _invalid("A provider duration component cannot be counted more than once")
    return output


def _status(snapshots, pathways):
    if snapshots and all(row.consideration_status == "no_change" for row in snapshots):
        return "supported"
    if any(row.pathway_type == "academic_intervention" for row in pathways):
        return (
            "partial"
            if any(
                row.unknown_duration_steps or row.evidence_sufficiency != "supported"
                for row in pathways
            )
            or any(row.consideration_status in {"needs_review", "rejected"} for row in snapshots)
            else "supported"
        )
    return "insufficient_evidence"


def _dependency_fingerprints(pathways, snapshots, evidence, inputs):
    references = {row.id: row for row in evidence}
    choices = {row.id: row for row in snapshots}
    fingerprints = {}
    for pathway in pathways:
        snapshot = choices[pathway.recommendation_id]
        ids = {citation.reference_id for step in pathway.steps for citation in step.citations}
        ids.update(
            citation.reference_id
            for prerequisite in pathway.prerequisites
            for citation in prerequisite.citations
        )
        dependency_evidence = {}
        for key in sorted(ids):
            value = references[key].model_dump(mode="json")
            # A fresh evaluation time alone does not change the underlying source.
            value["facts"].pop("as_of", None)
            dependency_evidence[key] = value
        fingerprints[pathway.key] = digest(
            {
                "recommendation": snapshot.recommendation.model_dump(mode="json"),
                "consideration_status": snapshot.consideration_status,
                "evidence": dependency_evidence,
                "steps": [row.model_dump(mode="json") for row in pathway.steps],
                "prerequisites": [row.model_dump(mode="json") for row in pathway.prerequisites],
            }
        )
    return fingerprints


def _reassessment(session, request, run, fingerprints):
    result = {
        "trigger": "explicit_new_immutable_plan_request",
        "dependency_fingerprints": fingerprints,
        "changed_pathway_keys": [],
        "unchanged_pathway_keys": [],
        "limitations": [
            "This compares supplied frozen snapshots; it is not continuous source monitoring."
        ],
    }
    if request.previous_plan_id is None:
        result["status"] = "not_requested"
        return result
    from shiftos.models import ActionPlanRun
    from shiftos.repositories.pathways import _previous_state

    previous = session.get(ActionPlanRun, request.previous_plan_id)
    previous_state = _previous_state(session, request.previous_plan_id, run)
    old = previous.result_json.get("reassessment", {}).get("dependency_fingerprints", {})
    result.update(
        status="compared_frozen_dependencies",
        previous_plan=previous_state,
        previous_dependency_fingerprints=old,
        changed_pathway_keys=sorted(
            key for key in set(old) | set(fingerprints) if old.get(key) != fingerprints.get(key)
        ),
        unchanged_pathway_keys=sorted(
            key for key in set(old) & set(fingerprints) if old[key] == fingerprints[key]
        ),
    )
    return result


def _phase4_context(session, request, run, settings):
    if request.phase4_analysis_id is None:
        return {
            "status": "not_linked",
            "limitation": "No Phase 4 result was supplied; no per-course findings are invented.",
        }
    from shiftos.repositories.pathways import _phase4_state

    state = _phase4_state(session, request.phase4_analysis_id, run, settings)
    analysis = session.get(AnalysisRun, request.phase4_analysis_id)
    findings = session.scalars(
        select(CourseFinding)
        .where(CourseFinding.run_id == analysis.id)
        .order_by(CourseFinding.course_id)
    ).all()
    return {
        "status": "linked_same_revision",
        **state,
        "summary": analysis.summary_json.get("summary", {}),
        "courses": [
            {
                "course_id": str(row.course_id),
                "review_flag": row.result_json.get("review_flag"),
                "needs_syllabus_confirmation": row.result_json.get("needs_syllabus_confirmation"),
                "is_final_curriculum_verdict": False,
            }
            for row in findings
        ],
    }


def evaluate(session, career_run_id, request: PlanRequest, settings, as_of) -> PlanResult:
    from shiftos.services.pathways.resources import admit_resources
    from shiftos.services.pathways.sdg import admit_sdgs

    run, career, rows, _, history = _load_parent(session, career_run_id, settings, as_of)
    snapshots = _snapshots(rows, career, history, request.recommendation_ids, as_of)
    request = request.model_copy(
        update={"recommendation_ids": [row.id for row in snapshots], "as_of": as_of}
    )
    resources, resource_evidence, resource_limits = admit_resources(
        session, request.resources, career, settings, as_of
    )
    evidence = {row.id: row for row in [*career.evidence, *resource_evidence]}
    for binding in request.prerequisites:
        prerequisite = session.get(Skill, binding.prerequisite_skill_id)
        if prerequisite is None:
            _invalid("A prerequisite has no registered source skill identity")
    pathways = _pathways(
        snapshots, resources, list(evidence.values()), request, as_of, run.programme_revision_id
    )
    alignments, sdg_evidence, sdg_limits = admit_sdgs(
        session,
        request.sdg_mappings,
        snapshots,
        list(evidence.values()),
        settings,
        as_of,
        run.is_synthetic,
    )
    for item in sdg_evidence:
        if item.id in evidence and evidence[item.id] != item:
            _invalid("Conflicting evidence shares one source identity")
        evidence[item.id] = item
    if len(evidence) > 300:
        _invalid("Action-plan evidence exceeds the 300-reference bound")
    scenarios, comparison = build_scenarios(
        career, snapshots, list(evidence.values()), request.scenarios, as_of
    )
    programme = session.get(Programme, run.programme_id)
    institution = session.get(Institution, run.institution_id)
    revision = session.get(ProgrammeRevision, run.programme_revision_id)
    overview = ProgrammeOverview(
        institution_id=run.institution_id,
        institution_name=institution.name,
        programme_id=run.programme_id,
        programme_name=programme.name,
        programme_revision_id=run.programme_revision_id,
        revision_label=revision.version_label,
        course_ids=career.course_ids,
        phase4_context=_phase4_context(session, request, run, settings),
        evidence_coverage={
            "course_count": len(career.course_ids),
            "occupation_count": len(career.occupations),
            "requirement_count": len(career.competencies),
            "coverage_states": {
                state: sum(row.state == state for row in career.competencies)
                for state in ("supported", "partial", "documented_gap", "unknown")
            },
            "source_reference_count": len(evidence),
        },
        limitations=career.limitations,
    )
    fingerprints = _dependency_fingerprints(pathways, snapshots, list(evidence.values()), request)
    result = PlanResult(
        programme_id=run.programme_id,
        programme_revision_id=run.programme_revision_id,
        career_run_id=run.id,
        career_fingerprint=run.fingerprint,
        as_of=as_of,
        is_synthetic=run.is_synthetic,
        status=_status(snapshots, pathways),
        overview=overview,
        career=career,
        recommendations=snapshots,
        pathways=pathways,
        resources=resources,
        scenarios=scenarios,
        comparison=comparison,
        sdg_alignments=alignments,
        review={
            "status": "proposed",
            "academic_approval": False,
            "operator_identity_limit": (
                "Existing token authenticates an operator, not a named academic reviewer."
            ),
            "implementation_authorised": False,
            "sections": [
                "A_programme_overview",
                "B_career_alignment",
                "C_competency_coverage",
                "D_academic_recommendations",
                "E_academic_pathways",
                "F_future_scenarios",
                "G_SDG_alignment",
                "H_academic_review",
            ],
            "overview_sha256": digest(overview.model_dump(mode="json")),
        },
        evidence=list(evidence.values()),
        permission_policy=career.permission_policy,
        inputs=request,
        reassessment=_reassessment(session, request, run, fingerprints),
        limitations=list(
            dict.fromkeys(
                [
                    *resource_limits,
                    *sdg_limits,
                    "All objectives, activities and assessments are future proposals "
                    "requiring academic review.",
                    "No attendance, enrolment or resource completion establishes "
                    "demonstrated technical competency.",
                    "Brave original-source admission remains PARTIAL; "
                    "this workflow makes no external research request.",
                    "Institutional substitution for personal hackathon matching/pathways "
                    "remains unconfirmed.",
                ]
            )
        ),
    )
    return validate_plan_result(result)


def validate_plan_result(result) -> PlanResult:
    from shiftos.services.pathways.resources import validate_resources
    from shiftos.services.pathways.sdg import validate_sdg_alignments

    result = PlanResult.model_validate(result)
    if result.inputs.as_of != result.as_of or result.as_of > datetime.now(UTC) + timedelta(
        seconds=1
    ):
        _invalid("Plan evidence cutoff changes its frozen request or lies in the future")
    career = validate_career_result(result.career)
    if (
        digest(career.model_dump(mode="json")) != result.career_fingerprint
        or career.programme_id != result.programme_id
        or career.programme_revision_id != result.programme_revision_id
        or career.is_synthetic != result.is_synthetic
        or career.as_of > result.as_of
        or result.permission_policy != career.permission_policy
    ):
        _invalid("Plan changes its parent career snapshot, lineage or source policy")
    evidence = {row.id: row for row in result.evidence}
    if len(evidence) != len(result.evidence):
        _invalid("Plan contains duplicate evidence identities")
    for item in career.evidence:
        if evidence.get(item.id) != item:
            _invalid("Plan changed or omitted frozen parent evidence")
    for item in evidence.values():
        if item.id not in {row.id for row in career.evidence} and item.kind not in {
            "learning_resource",
            "sdg",
        }:
            _invalid("Plan introduces an unsupported source type outside its parent snapshot")
        if (
            not item.internal_eligible
            or not item.rights.internal_analysis_allowed
            or not item.rights.excerpt_output_allowed
            or item.review_status == "rejected"
            or (item.retrieved_at and item.retrieved_at > result.as_of)
        ):
            _invalid("Plan evidence is not permitted or was not known at the cutoff")
    expected_recommendations = {row.key: row for row in career.recommendations}
    if len({row.id for row in result.recommendations}) != len(result.recommendations):
        _invalid("Plan contains duplicate recommendation identities")
    for snapshot in result.recommendations:
        recommendation = snapshot.recommendation
        if (
            expected_recommendations.get(recommendation.key) != recommendation
            or digest(recommendation.model_dump(mode="json")) != snapshot.version_sha256
        ):
            _invalid("Plan changes its exact parent academic recommendation")
        previous = None
        for review in snapshot.reviews:
            try:
                reviewed_at = datetime.fromisoformat(review["reviewed_at"])
                identity = UUID(review["id"])
                if (
                    reviewed_at.tzinfo is None
                    or reviewed_at > result.as_of
                    or review["recommendation_id"] != str(snapshot.id)
                    or review["recommendation_version"] != snapshot.version_sha256
                    or review["actor"] != "authenticated_analysis_operator"
                    or review["decision"]
                    not in {
                        "needs_evidence",
                        "under_review",
                        "approved",
                        "rejected",
                        "no_change_required",
                    }
                ):
                    raise ValueError
                order = (reviewed_at, identity)
                if previous is not None and order <= previous:
                    raise ValueError
                previous = order
            except (KeyError, TypeError, ValueError):
                _invalid("Plan consideration review has inconsistent version, actor or time")
        if snapshot.consideration_status != _consideration(recommendation, snapshot.reviews):
            _invalid("Plan invents consideration eligibility or overrides the latest review")
    if result.inputs.recommendation_ids and set(result.inputs.recommendation_ids) != {
        row.id for row in result.recommendations
    }:
        _invalid("Plan recommendation inventory changes the frozen request")
    if (
        result.overview.programme_id != result.programme_id
        or result.overview.programme_revision_id != result.programme_revision_id
        or result.overview.course_ids != career.course_ids
        or result.review.get("overview_sha256") != digest(result.overview.model_dump(mode="json"))
    ):
        _invalid("Plan programme overview or course inventory changes its frozen revision")
    validate_resources(result.resources, result.evidence, result.as_of)
    for resource in result.resources:
        _check_citations(resource.citations, evidence)
    canonical = _pathways(
        result.recommendations,
        result.resources,
        result.evidence,
        result.inputs,
        result.as_of,
        result.programme_revision_id,
    )
    if result.pathways != canonical:
        _invalid("Plan pathways change canonical eligibility, order, activities or duration")
    for pathway in result.pathways:
        _validate_dependency_graph(
            [(row.key, row.position, row.depends_on) for row in pathway.steps]
        )
        _check_citations(pathway.citations, evidence)
        for step in pathway.steps:
            _check_citations(step.citations, evidence)
            _check_citations(step.duration.citations, evidence)
    scenarios, comparison = build_scenarios(
        career, result.recommendations, result.evidence, result.inputs.scenarios, result.as_of
    )
    if result.scenarios != scenarios or result.comparison != comparison:
        _invalid("Plan scenario outputs change their assumptions or deterministic comparison")
    validate_sdg_alignments(
        result.sdg_alignments,
        result.recommendations,
        result.evidence,
        result.inputs.sdg_mappings,
        result.as_of,
    )
    if result.status != _status(result.recommendations, result.pathways):
        _invalid("Plan status changes its evidence and consideration gates")
    if (
        result.review.get("status") != "proposed"
        or result.review.get("academic_approval") is not False
        or result.review.get("implementation_authorised") is not False
    ):
        _invalid(
            "A generated plan cannot invent institutional approval or implementation authority"
        )
    fingerprints = _dependency_fingerprints(
        result.pathways, result.recommendations, result.evidence, result.inputs
    )
    if result.reassessment.get("dependency_fingerprints") != fingerprints:
        _invalid("Plan reassessment changes its source/requirement dependency fingerprints")
    if result.inputs.previous_plan_id is None:
        if (
            result.reassessment.get("status") != "not_requested"
            or result.reassessment.get("changed_pathway_keys") != []
            or result.reassessment.get("unchanged_pathway_keys") != []
        ):
            _invalid("Plan invents a previous-snapshot reassessment")
    else:
        previous = result.reassessment.get("previous_dependency_fingerprints")
        receipt = result.reassessment.get("previous_plan", {})
        if not isinstance(previous, dict) or receipt.get("id") != str(
            result.inputs.previous_plan_id
        ):
            _invalid("Plan reassessment lacks its exact previous-snapshot receipt")
        changed = sorted(
            key
            for key in set(previous) | set(fingerprints)
            if previous.get(key) != fingerprints.get(key)
        )
        unchanged = sorted(
            key for key in set(previous) & set(fingerprints) if previous[key] == fingerprints[key]
        )
        if (
            result.reassessment.get("status") != "compared_frozen_dependencies"
            or result.reassessment.get("changed_pathway_keys") != changed
            or result.reassessment.get("unchanged_pathway_keys") != unchanged
        ):
            _invalid("Plan reassessment changes its dependency comparison")
    return result
