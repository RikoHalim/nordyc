"""Reproducible qualitative planning assumptions, never workforce forecasts."""

from shiftos.schemas.pathways import (
    FutureScenario,
    ScenarioComparison,
    ScenarioInput,
    ScenarioPriority,
)
from shiftos.services.analysis.retrieval import _date_interval

DIMENSIONS = [
    "competency_coverage",
    "evidence_sufficiency",
    "assessment_review_priority",
    "academic_dependencies",
    "minimum_intervention_and_no_change",
]


def _normal(value):
    return " ".join(value.split())


def _validate_citations(citations, evidence):
    for citation in citations:
        item = evidence.get(citation.reference_id)
        if (
            item is None
            or not item.internal_eligible
            or not item.rights.internal_analysis_allowed
            or not item.rights.excerpt_output_allowed
            or not _normal(citation.quote)
            or _normal(citation.quote) not in _normal(item.excerpt)
        ):
            raise ValueError("Scenario citation does not match admitted source evidence")


def _assumptions(inputs):
    supplied = {item.key: item for item in inputs}
    defaults = [
        ScenarioInput(
            key="gradual_workforce_transformation",
            assumption="prioritise_incremental_coverage",
            rationale=(
                "Hypothetical planning assumption: review incremental coverage changes "
                "while preserving disciplinary foundations and the no-change option."
            ),
        ),
        ScenarioInput(
            key="accelerated_ai_adoption",
            assumption="prioritise_assessment_review",
            rationale=(
                "Hypothetical planning assumption: prioritise assessment review for "
                "eligible cited professional tasks if their adoption becomes more rapid. "
                "No adoption rate, job displacement or deadline is predicted."
            ),
        ),
    ]
    return [supplied.get(item.key, item) for item in defaults]


def build_scenarios(career, snapshots, evidence, inputs, as_of=None):
    """Compare the same recommendations and evidence under two explicit assumptions."""
    references = {item.id: item for item in evidence}
    cutoff = as_of or career.as_of

    def current_task(item):
        earliest, _, precision = _date_interval(item.publication_date)
        return bool(earliest and precision == "day" and 0 <= (cutoff.date() - earliest).days <= 730)

    scenarios = []
    occupations = {item.occupation_id: item for item in career.occupations}
    for assumption in _assumptions(inputs):
        _validate_citations(assumption.supporting_citations, references)
        _validate_citations(assumption.contradicting_citations, references)
        priorities = []
        accelerated = assumption.assumption == "prioritise_assessment_review"
        for snapshot in snapshots:
            recommendation = snapshot.recommendation
            observed = set()
            for occupation_id in recommendation.occupation_ids:
                occupation = occupations.get(occupation_id)
                if occupation and occupation.ai_transformation.get("status") == "AI-TRANSFORMING":
                    observed.update(occupation.ai_transformation.get("reference_ids", []))
            supported_task = any(
                reference_id in observed
                and (item := references.get(reference_id)) is not None
                and item.kind == "ai_evidence"
                and item.scope == "ai_task_context"
                and item.review_status == "reviewed"
                and not item.historical_context_only
                and current_task(item)
                for reference_id in {
                    citation.reference_id for citation in assumption.supporting_citations
                }
            )
            if snapshot.consideration_status == "no_change":
                priority = "monitor"
                reason = "The recorded no-change outcome is preserved under both assumptions."
            elif (
                snapshot.consideration_status != "eligible"
                or recommendation.evidence_sufficiency == "insufficient_evidence"
                or recommendation.category == "request_review"
            ):
                priority = "review_first"
                reason = (
                    "Missing evidence, rejection or consideration review prevents a substantive "
                    "intervention; the assumption cannot establish coverage or approval."
                )
            elif accelerated and supported_task and not assumption.contradicting_citations:
                priority = "conditional_priority"
                reason = (
                    "Under this explicit assumption, review the already eligible assessment "
                    "proposal earlier for the exact cited observed task; this is an engineering "
                    "priority band, not a forecast or new curriculum decision."
                )
            else:
                priority = "review_first"
                reason = (
                    "Retain the minimum sufficient intervention and staged academic review. "
                    "No sufficiently scoped, uncontradicted task evidence justifies escalation."
                )
            priorities.append(
                ScenarioPriority(
                    recommendation_id=snapshot.id,
                    priority=priority,
                    rationale=reason,
                    conditions=[
                        "The parent coverage findings and workforce calculations remain unchanged.",
                        "Review conflicting and missing evidence before implementation.",
                        "Authenticated operator consideration is not institutional approval.",
                    ],
                )
            )
        scenarios.append(
            FutureScenario(
                key=assumption.key,
                name=(
                    "Accelerated AI adoption — hypothetical planning"
                    if assumption.key == "accelerated_ai_adoption"
                    else "Gradual workforce transformation — hypothetical planning"
                ),
                description=(
                    "Compare review priorities under the stated assumption, with unchanged "
                    "observed evidence and parent academic recommendations. No job, wage, "
                    "placement, displacement or numerical adoption forecast is produced."
                ),
                planning_horizon=assumption.planning_horizon,
                assumption=assumption,
                occupation_ids=list(
                    dict.fromkeys(
                        value
                        for snapshot in snapshots
                        for value in snapshot.recommendation.occupation_ids
                    )
                ),
                skill_ids=list(
                    dict.fromkeys(
                        snapshot.recommendation.skill_id
                        for snapshot in snapshots
                        if snapshot.recommendation.skill_id is not None
                    )
                ),
                priorities=priorities,
                supporting_citations=assumption.supporting_citations,
                contradicting_citations=assumption.contradicting_citations,
                uncertainties=[
                    "Assumptions are hypothetical and do not measure future adoption.",
                    "Source scope, dates, geography and unknown coverage remain binding.",
                    "No action flip is required; unsupported sensitivity remains unknown.",
                ],
                comparison_dimensions=DIMENSIONS,
            )
        )
    left, right = (
        {row.recommendation_id: row.priority for row in item.priorities} for item in scenarios
    )
    changed = [snapshot.id for snapshot in snapshots if left[snapshot.id] != right[snapshot.id]]
    unchanged = [snapshot.id for snapshot in snapshots if snapshot.id not in changed]
    robust = [
        snapshot.id
        for snapshot in snapshots
        if left[snapshot.id] == right[snapshot.id]
        and snapshot.consideration_status != "rejected"
        and snapshot.recommendation.category in {"request_review", "no_change"}
    ]
    return scenarios, ScenarioComparison(
        scenario_keys=[item.key for item in scenarios],
        dimensions=DIMENSIONS,
        changed_recommendation_ids=changed,
        unchanged_recommendation_ids=unchanged,
        no_regret_recommendation_ids=robust,
        explanation=(
            "Compare the same recommendation identities across both labelled assumptions. "
            "Only a scoped review-priority band can change; parent evidence, coverage, "
            "minimum interventions and no-change options are preserved."
        ),
        limitations=[
            "Robustness means procedural consistency here, not proven intervention efficacy.",
            "No employment probability or quantified future labour demand is calculated.",
        ],
    )
