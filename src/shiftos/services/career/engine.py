"""Deterministic source-grounded requirements, curriculum coverage and review options.

Titles never establish competency. Explicit reviewed assertions select exact stored
passages; the service validates their identity, scope, permissions and time boundary.
No network, model, guessed crosswalk or workforce arithmetic is implemented here.
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from shiftos.core.enums import ContentStatus, CourseType, DocumentKind
from shiftos.core.errors import DomainError
from shiftos.models import (
    AIImpactEvidence,
    Course,
    Dataset,
    DatasetVersion,
    Document,
    DocumentAnchor,
    EvidenceReference,
    Institution,
    Occupation,
    OccupationSkill,
    Programme,
    ProgrammeRevision,
    Skill,
    Source,
    WorkforceObservation,
)
from shiftos.schemas.analysis import EvidenceItem
from shiftos.schemas.career import (
    AcademicRecommendation,
    ActionOption,
    AlignmentMeasure,
    CareerCitation,
    CareerRequest,
    CareerResult,
    CourseSupport,
    OccupationAlignment,
    RequirementFinding,
)
from shiftos.services.analysis.orchestrator import _permissions
from shiftos.services.analysis.retrieval import (
    _date_interval,
    _public_url,
    _rights,
    discipline_for,
)
from shiftos.services.evidence.trends import compare_observations, occupation_ai_transformation

MAX_EVIDENCE = 300
MAX_REQUIREMENTS = 1000
MAX_EXCERPT = 2000
WITHDRAWAL_FLAGS = ("extraction_candidate", "retracted", "superseded", "correction_pending")


def _invalid(message):
    raise DomainError("CAREER_INPUT_INVALID", message, 422)


def _normal(value):
    return " ".join(value.split())


def _citation(item):
    return CareerCitation(reference_id=item.id, quote=item.excerpt[:MAX_EXCERPT])


def _unique_citations(citations):
    return list({(row.reference_id, row.quote): row for row in citations}.values())


def _current(item):
    return item.review_status == "reviewed" and not item.historical_context_only


class _Context:
    def __init__(self, session, programme, revision, courses, settings, as_of):
        self.session, self.programme, self.revision = session, programme, revision
        self.courses = {row.id: row for row in courses}
        self.synthetic, self.as_of = programme.is_synthetic, as_of
        self.permissions, self.permission_policy = _permissions(settings)
        self.evidence = {}
        self.limitations = []

    def remember(self, item):
        if item.id not in self.evidence and len(self.evidence) >= MAX_EVIDENCE:
            self.limitations.append("evidence_budget_exhausted")
            return None
        previous = self.evidence.get(item.id)
        if previous is not None and previous != item:
            _invalid("The same evidence identity has conflicting asserted support")
        self.evidence[item.id] = item
        return item

    def record(self, row, kind, scope, expected="occupation_requirement"):
        version = self.session.get(DatasetVersion, row.version_id)
        reference = self.session.get(EvidenceReference, row.evidence_id)
        source = self.session.get(Source, version.source_id) if version else None
        dataset = self.session.get(Dataset, version.dataset_id) if version else None
        if not all((version, reference, source, dataset)):
            _invalid("An evidence record has incomplete source lineage")
        if reference.version_id != version.id:
            _invalid("An evidence pointer belongs to a different source version")
        if not all(
            value.is_synthetic == self.synthetic for value in (row, version, reference, source)
        ):
            self.limitations.append("inconsistent_synthetic_lineage")
            return None
        if (
            version.retrieved_at > self.as_of
            or (source.collected_at and source.collected_at > self.as_of)
            or (source.published_at and source.published_at > self.as_of)
        ):
            self.limitations.append("source_not_known_at_cutoff")
            return None
        containers = [
            row.metadata_json or {},
            reference.metadata_json or {},
            version.metadata_json or {},
        ]
        if reference.review_status == "rejected" or any(
            container.get(flag) for container in containers for flag in WITHDRAWAL_FLAGS
        ):
            self.limitations.append("source_rejected_or_correction_pending")
            return None
        actual_class = str(source.evidence_class)
        if actual_class != ("synthetic_demo" if self.synthetic else expected):
            self.limitations.append("incompatible_evidence_class")
            return None
        if not self.synthetic and not _public_url(source.url):
            self.limitations.append("source_has_no_safe_public_identity")
            return None
        rights = _rights(
            row, version, self.permissions.get(dataset.registry_key, {}), self.synthetic, reference
        )
        if not rights.internal_analysis_allowed or not rights.excerpt_output_allowed:
            self.limitations.append("source_use_or_output_not_permitted")
            return None
        earliest, latest, precision = _date_interval(version.publication_date)
        if earliest and earliest > self.as_of.date():
            self.limitations.append("source_publication_after_cutoff")
            return None
        maximum_age = 550 if kind == "workforce" else 730 if kind == "ai_evidence" else 1825
        historical = (
            precision != "day" or not earliest or (self.as_of.date() - earliest).days > maximum_age
        )
        if kind == "workforce":
            if row.period_end > self.as_of.date():
                return None
            historical = historical or (self.as_of.date() - row.period_end).days > 550
        facts = {
            "external_id": row.external_id,
            "content_sha256": version.content_sha256,
            "parser_version": version.parser_version,
            "context_sha256": version.context_sha256,
        }
        for name in (
            "taxonomy",
            "label",
            "occupation_id",
            "skill_id",
            "relationship",
            "geography",
            "indicator",
            "unit",
        ):
            value = getattr(row, name, None)
            if value is not None:
                facts[name] = str(value)
        for key in ("edition", "language", "source_language", "geography"):
            for container in (version.metadata_json or {}, row.metadata_json or {}):
                value = container.get(key)
                if isinstance(value, str):
                    facts[key] = value[:300]
        limitations = (
            ["benchmark_not_university_teaching_or_Malaysian_demand"]
            if expected == "occupation_requirement"
            else []
        )
        if precision != "day":
            limitations.append("unknown_or_imprecise_source_date")
        if historical:
            limitations.append("historical_context_not_current_requirement_assurance")
        if reference.review_status != "reviewed":
            limitations.append("source_interpretation_requires_review")
        if kind == "workforce":
            limitations.append("occupation_observations_do_not_measure_skill_demand")
        return self.remember(
            EvidenceItem(
                id=f"{kind}:{row.id}",
                kind=kind,
                record_id=row.id,
                version_id=version.id,
                evidence_reference_id=reference.id,
                source_id=source.id,
                dataset_key=dataset.registry_key,
                evidence_class=actual_class,
                scope=scope,
                source_url=_public_url(source.url),
                publisher=source.publisher,
                title=source.title,
                locator=reference.locator,
                excerpt=reference.excerpt[:MAX_EXCERPT],
                publication_date=version.publication_date,
                date_precision=precision,
                retrieved_at=version.retrieved_at,
                observation_start=str(row.period_start) if kind == "workforce" else None,
                observation_end=str(row.period_end) if kind == "workforce" else None,
                review_status=reference.review_status,
                is_synthetic=self.synthetic,
                rights=rights,
                internal_eligible=True,
                model_eligible=rights.external_model_allowed,
                historical_context_only=historical,
                identity_reviewed=False,
                relevance_basis=["explicit_identifier_not_title_match"],
                limitations=limitations,
                facts=facts,
            )
        )

    def anchor(self, assertion, skill, *, gap=False):
        anchor = self.session.get(DocumentAnchor, assertion.anchor_id)
        document = self.session.get(Document, anchor.document_id) if anchor else None
        if anchor is None or document is None:
            _invalid("The supplied curriculum anchor does not exist")
        if document.programme_revision_id != self.revision.id:
            _invalid("The supplied curriculum anchor belongs to another revision")
        course = None if gap else self.courses.get(assertion.course_id)
        if gap:
            if document.course_id is not None:
                _invalid("A programme-wide absence audit cannot be a single-course document")
        elif course is None or document.course_id != course.id:
            _invalid("The supplied passage is not linked to the asserted course")
        if not all(row.is_synthetic == self.synthetic for row in (anchor, document)):
            _invalid("Curriculum passage and programme belong to different evidence lanes")
        if document.document_kind not in {DocumentKind.SYLLABUS, DocumentKind.SUPPORTING}:
            self.limitations.append("inventory_document_cannot_establish_competency")
            return None
        if document.uploaded_at > self.as_of:
            self.limitations.append("curriculum_not_known_at_cutoff")
            return None
        quote = _normal(assertion.quote)
        excerpt = anchor.excerpt[:MAX_EXCERPT]
        if not quote or quote not in _normal(excerpt):
            _invalid("Curriculum quote does not match its bounded stored source passage")
        metadata = document.metadata_json or {}
        if (
            metadata.get("content_reviewed") is not True
            or any(metadata.get(key) for key in WITHDRAWAL_FLAGS)
            or document.content_status in {ContentStatus.FAILED, ContentStatus.NEEDS_OCR}
        ):
            self.limitations.append("curriculum_passage_not_reviewed")
            return None
        rights = _rights(document, document, {}, self.synthetic)
        if not rights.internal_analysis_allowed or not rights.excerpt_output_allowed:
            self.limitations.append("curriculum_use_or_output_not_permitted")
            return None
        if course is not None:
            source_id = course.source_id
        else:
            source_ids = {row.source_id for row in self.courses.values() if row.source_id}
            supplied = metadata.get("source_id")
            source_id = UUID(str(supplied)) if supplied else self.programme.source_id
            if not source_id and len(source_ids) == 1:
                source_id = next(iter(source_ids))
        source = self.session.get(Source, source_id) if source_id else None
        if source is None or source.is_synthetic != self.synthetic:
            self.limitations.append("curriculum_source_identity_missing")
            return None
        if (
            (source.published_at and source.published_at > self.as_of)
            or (source.collected_at and source.collected_at > self.as_of)
            or (
                not self.synthetic
                and (
                    str(source.evidence_class) != "verified_university_fact"
                    or not _public_url(source.url)
                    or (course is not None and not course.is_verified)
                )
            )
        ):
            self.limitations.append("curriculum_fact_identity_unverified")
            return None
        reviewed = assertion.reviewed and assertion.reviewed_at <= self.as_of
        if gap:
            declared = metadata.get("negative_skill_ids", [])
            if (
                not reviewed
                or not assertion.completeness_confirmed
                or set(assertion.covered_course_ids) != set(self.courses)
                or len(assertion.covered_course_ids) != len(self.courses)
                or metadata.get("gap_reviewed") is not True
                or not isinstance(declared, list)
                or str(skill.id) not in declared
            ):
                self.limitations.append("programme_wide_negative_audit_not_confirmed")
                return None
        published = source.published_at.date().isoformat() if source.published_at else None
        effective = self.revision.effective_date
        historical = not self.synthetic and (
            not effective or (self.as_of.date() - effective).days > 1825
        )
        facts = {
            "document_id": str(document.id),
            "document_sha256": document.content_sha256,
            "programme_revision_id": str(self.revision.id),
            "skill_id": str(skill.id),
            "course_id": str(course.id) if course else None,
            "course_type": str(course.course_type) if course else None,
            "reviewed": bool(reviewed),
            "reviewed_at": assertion.reviewed_at.isoformat(),
            "support": "negative_audit" if gap else assertion.support,
            "extent": "full" if gap else assertion.extent,
            "demonstration_reviewed": metadata.get("demonstration_reviewed") is True,
            "negative_audit_reviewed": bool(gap),
            "covered_course_ids": sorted(str(value) for value in assertion.covered_course_ids)
            if gap
            else [],
        }
        limitations = ["reviewed_curriculum_intent_is_not_individual_graduate_competence"]
        if historical:
            limitations.append("curriculum_effective_date_unknown_or_historical")
        kind = "curriculum_gap" if gap else "curriculum"
        return self.remember(
            EvidenceItem(
                id=f"{kind}:{anchor.id}:{skill.id}",
                kind=kind,
                record_id=anchor.id,
                version_id=self.revision.id,
                evidence_reference_id=anchor.id,
                source_id=source.id,
                evidence_class=str(source.evidence_class),
                scope="verified_syllabus",
                source_url=_public_url(source.url),
                publisher=source.publisher,
                title=source.title,
                locator=anchor.locator,
                excerpt=excerpt,
                publication_date=published,
                date_precision="day" if published else "unknown",
                retrieved_at=document.uploaded_at,
                review_status="reviewed" if reviewed else "needs_review",
                is_synthetic=self.synthetic,
                rights=rights,
                internal_eligible=True,
                model_eligible=rights.external_model_allowed,
                historical_context_only=historical,
                identity_reviewed=False,
                relevance_basis=["explicit_reviewed_competency_assertion_not_course_title"],
                limitations=limitations,
                facts=facts,
            )
        )


def _support(context, skill, assertions):
    supports = []
    for assertion in assertions:
        item = context.anchor(assertion, skill)
        if item is None:
            continue
        support = assertion.support
        limitations = list(item.limitations)
        if not _current(item):
            support = "unknown"
            limitations.append("curriculum_mapping_unreviewed_or_not_current")
        if support == "demonstrated" and not item.facts["demonstration_reviewed"]:
            support = "unknown"
            limitations.append("assessed_demonstration_not_verified")
        if support == "possible_association":
            limitations.append("possible_association_does_not_establish_coverage")
        extent = assertion.extent
        if item.facts.get("course_type") != CourseType.COMPULSORY:
            extent = "partial"
            limitations.append("elective_or_unknown_course_not_universal_coverage")
        supports.append(
            CourseSupport(
                course_id=assertion.course_id,
                support=support,
                extent=extent,
                citations=[CareerCitation(reference_id=item.id, quote=assertion.quote)],
                limitations=limitations,
            )
        )
    return supports


def _requirement(context, mapping, occupation, relation, skill, items, assertions, gaps):
    supports = _support(context, skill, assertions)
    audits = []
    for gap in gaps:
        item = context.anchor(gap, skill, gap=True)
        if item is not None and _current(item):
            audits.append(CareerCitation(reference_id=item.id, quote=gap.quote))
    fresh = (
        mapping.reviewed
        and mapping.reviewed_at <= context.as_of
        and all(_current(item) for item in items)
    )
    demonstrated = [
        row for row in supports if row.support == "demonstrated" and row.extent == "full"
    ]
    positive = [row for row in supports if row.support in {"demonstrated", "documented_intent"}]
    state, support_type = "unknown", "unknown"
    explanation = "Coverage is unknown; missing documentation does not establish absence."
    limitations = [
        "no_title_based_competency_inference",
        "no_individual_employment_or_graduate_proficiency_claim",
    ]
    if not fresh:
        limitations.append("requirement_or_programme_mapping_not_reviewed_current")
    elif audits and positive:
        limitations.append("conflicting_curriculum_evidence_requires_academic_review")
        explanation = (
            "Reviewed positive and negative curriculum assertions conflict; no gap is confirmed."
        )
    elif audits:
        state = "documented_gap"
        explanation = (
            "An explicit reviewed audit states a deficiency across the complete "
            "listed programme revision."
        )
    elif demonstrated:
        state, support_type = "supported", "demonstrated"
        explanation = (
            "A reviewed assessed passage supports the bounded competency assertion; "
            "it does not establish every graduate's proficiency."
        )
    elif positive:
        state = "partial"
        support_type = (
            "demonstrated"
            if any(row.support == "demonstrated" for row in positive)
            else "documented_intent"
        )
        explanation = (
            "Reviewed curricular intent or partial assessed support exists; "
            "full demonstrated coverage is not established."
        )
    elif any(row.support == "possible_association" for row in supports):
        support_type = "possible_association"
    requirement_type = relation.relationship.casefold()
    if requirement_type not in {"essential", "optional"}:
        requirement_type = "unknown"
        state, support_type = "unknown", "unknown"
        limitations.append("unrecognised_requirement_type")
    if requirement_type == "optional":
        limitations.append("optional_requirement_not_universal_course_mandate")
    citations = [_citation(item) for item in items]
    citations.extend(citation for row in supports for citation in row.citations)
    citations.extend(audits)
    return RequirementFinding(
        occupation_id=occupation.id,
        relationship_id=relation.id,
        skill_id=skill.id,
        skill_name=skill.label,
        requirement_type=requirement_type,
        state=state,
        support_type=support_type,
        courses=supports,
        citations=_unique_citations(citations),
        explanation=explanation,
        evidence_needed=[]
        if state == "supported"
        else [
            "Confirm applicable occupational scope and curriculum/assessment support "
            "with academic reviewers."
        ],
        limitations=limitations,
    )


def _measure(requirements, complete, current):
    essential = [row for row in requirements if row.requirement_type == "essential"]
    known = [row for row in essential if row.state in {"supported", "documented_gap"}]
    numerator = sum(
        row.state == "supported" and row.support_type == "demonstrated" for row in essential
    )
    reason = None
    if not essential:
        reason = "No admissible essential requirement set is available."
    elif (
        not complete
        or not current
        or any(row.requirement_type == "unknown" for row in requirements)
    ):
        reason = "Requirement completeness, currentness or review is not established."
    elif len(known) != len(essential):
        reason = (
            "Unknown, partial or intended coverage cannot be scored "
            "as demonstrated coverage or zero."
        )
    return AlignmentMeasure(
        value=round(100 * numerator / len(essential), 4) if reason is None else None,
        numerator=numerator,
        denominator=len(essential),
        assessed_requirements=len(known),
        unknown_requirements=len(essential) - len(known),
        abstention_reason=reason,
    )


def _alignment_status(requirements, complete, current):
    essential = [value for value in requirements if value.requirement_type == "essential"]
    if (
        essential
        and complete
        and current
        and all(value.state == "supported" for value in essential)
    ):
        return "supported"
    if current and any(value.state != "unknown" for value in requirements):
        return "partial"
    return "insufficient_evidence"


def _programme_status(alignments, limitations):
    if {"evidence_budget_exhausted", "requirement_budget_exhausted"} & set(limitations):
        return "insufficient_evidence"
    states = {row.status for row in alignments}
    if states == {"supported"}:
        return "supported"
    return "partial" if states & {"supported", "partial"} else "insufficient_evidence"


def _context_signals(context, occupation):
    rows = context.session.scalars(
        select(WorkforceObservation)
        .where(WorkforceObservation.occupation_id == occupation.id)
        .order_by(WorkforceObservation.period_end, WorkforceObservation.id)
        .limit(101)
    ).all()
    groups, output = defaultdict(list), []
    for row in rows[:100]:
        item = context.record(row, "workforce", "workforce_context", "dated_workforce_signal")
        if item is not None:
            groups[(row.geography, row.indicator, row.unit)].append((row, item))
    for values in list(groups.values())[:5]:
        if len(values) < 2:
            continue
        before, after = values[-2:]
        if (before[0].period_start, before[0].period_end) == (
            after[0].period_start,
            after[0].period_end,
        ):
            context.limitations.append("conflicting_or_duplicate_workforce_period_requires_review")
            continue
        result = compare_observations(context.session, before[0].id, after[0].id)
        output.append(
            {
                "classification": result.classification,
                "compatible": result.compatible,
                "before_reference_id": before[1].id,
                "after_reference_id": after[1].id,
                "absolute_change": str(result.absolute_change)
                if result.absolute_change is not None
                else None,
                "percentage_change": str(result.percentage_change)
                if result.percentage_change is not None
                else None,
                "population_level": result.population_level,
                "measurement_kind": result.measurement_kind,
                "time_horizon": result.time_horizon,
                "fingerprint": result.fingerprint,
                "historical_context_only": before[1].historical_context_only
                or after[1].historical_context_only,
                "geography": after[0].geography,
                "period_end": str(after[0].period_end),
                "limitations": result.limitations,
                "method": result.policy.model_dump(mode="json"),
            }
        )
    ai = {
        "status": "INSUFFICIENT_EVIDENCE",
        "is_ai_transforming": None,
        "reference_ids": [],
        "limitations": [
            "No permitted reviewed dated occupation-task capability establishes transformation.",
            "Exposure is not replacement probability.",
        ],
    }
    # Reuse the established task method, then retain only explicitly admitted exact-ID evidence.
    checked = occupation_ai_transformation(context.session, occupation.id)
    for evidence in checked.evidence:
        row = context.session.get(AIImpactEvidence, evidence.evidence.id)
        if row.occupation_id != occupation.id:
            continue
        item = context.record(row, "ai_evidence", "ai_task_context", "dated_ai_capability")
        if item is not None and _current(item) and evidence.supports_transformation:
            ai["reference_ids"].append(item.id)
    if ai["reference_ids"]:
        ai.update(
            status="AI-TRANSFORMING",
            is_ai_transforming=True,
            limitations=[
                "Observed professional task evidence applies only to its stated "
                "setting, model and period.",
                "No job replacement, Malaysian adoption or skill-demand claim is established.",
            ],
        )
    return output, ai


def _recommendations(revision_id, requirements):
    grouped = defaultdict(list)
    for requirement in requirements:
        grouped[requirement.skill_id].append(requirement)
    recommendations = []
    for skill_id, values in list(grouped.items())[:99]:
        states = {row.state for row in values}
        occupation_count = len({row.occupation_id for row in values})
        essential_count = sum(row.requirement_type == "essential" for row in values)
        optional_count = sum(row.requirement_type == "optional" for row in values)
        if "unknown" in states:
            category, sufficiency, priority = (
                "request_review",
                "insufficient_evidence",
                "review_first",
            )
            action = (
                "Review the applicable competency requirement and obtain verified "
                "curriculum/assessment support."
            )
        elif "documented_gap" in states:
            category, sufficiency, priority = (
                "review_learning_outcome",
                "supported",
                "supported_need",
            )
            action = (
                "Review a bounded existing learning outcome against the documented "
                "deficiency before choosing a curriculum intervention."
            )
        elif "partial" in states:
            category, sufficiency, priority = "introduce_assessment", "partial", "review_first"
            action = (
                "Review whether an appropriate assessed exercise can verify "
                "the documented intended competency."
            )
        else:
            category, sufficiency, priority = "no_change", "supported", "monitor"
            action = (
                "Retain the documented arrangement subject to academic review "
                "and evidence monitoring."
            )
        citations = _unique_citations(
            [citation for value in values for citation in value.citations]
        )
        no_change = ActionOption(
            category="no_change",
            action=(
                "Retain current arrangements while monitoring the identified "
                "evidence and review conditions."
            ),
            rationale=(
                "Human reviewers may decide that no curriculum change is justified; "
                "uncertainty is not proof of a deficiency."
            ),
            conditions=[
                "Record the academic decision and reassess when the linked evidence changes."
            ],
        )
        recommendations.append(
            AcademicRecommendation(
                key=f"skill-{skill_id}",
                programme_revision_id=revision_id,
                occupation_ids=list(dict.fromkeys(row.occupation_id for row in values)),
                skill_id=skill_id,
                course_ids=list(
                    dict.fromkeys(course.course_id for value in values for course in value.courses)
                ),
                category=category,
                action=action,
                rationale=(
                    f"The source-grounded coverage state for {values[0].skill_name} "
                    f"is {', '.join(sorted(states))}; titles, job counts and exposure "
                    "do not establish curricular need."
                ),
                minimum_sufficient_intervention=(
                    "Start with the stated review or smallest justified assessment/content "
                    "adjustment; compare the unchanged arrangement before escalation."
                ),
                alternatives=[
                    ActionOption(
                        category="request_review",
                        action=(
                            "Request the missing source, applicability or assessment confirmation."
                        ),
                        rationale=(
                            "Resolve the precise uncertainty before implementing "
                            "a larger intervention."
                        ),
                        conditions=["Use verified passages and record reviewer rationale."],
                    )
                ],
                no_change_option=no_change,
                competency_objective=(
                    "Proposed review objective: verify source-supported preparation for "
                    f"{values[0].skill_name}; this is not a claim of existing university teaching."
                ),
                implementation_considerations=[
                    "Human academic approval required.",
                    "Cost, duration, partners and learning resources remain unknown "
                    "unless independently verified.",
                    "No personal competence or employment probability is inferred.",
                ],
                evidence_sufficiency=sufficiency,
                priority=priority,
                priority_basis=(
                    f"{occupation_count} explicitly mapped occupation context(s); "
                    f"{essential_count} essential and {optional_count} optional "
                    f"requirement(s). Coverage states: {', '.join(sorted(states))}. "
                    f"Minimum proposed scope: {category}, subject to academic review. "
                    "These counts describe the selected source requirements, not labour demand; "
                    "unknown coverage receives evidence review before a larger intervention."
                ),
                citations=citations,
                limitations=list(
                    dict.fromkeys(
                        limitation for value in values for limitation in value.limitations
                    )
                ),
                review_status="needs_evidence"
                if sufficiency == "insufficient_evidence"
                else "proposed",
            )
        )
    if not recommendations:
        option = ActionOption(
            category="no_change",
            action="Keep existing arrangements pending evidence review.",
            rationale=(
                "No supported occupational mapping or deficiency justifies a curriculum change."
            ),
        )
        recommendations.append(
            AcademicRecommendation(
                key="career-evidence-review",
                programme_revision_id=revision_id,
                category="request_review",
                action=(
                    "Obtain a reviewed programme-to-occupation mapping "
                    "and eligible requirement evidence."
                ),
                rationale="Career alignment cannot be established from programme or course titles.",
                minimum_sufficient_intervention=(
                    "Gather the missing reviewed evidence before considering "
                    "a curricular intervention."
                ),
                alternatives=[option],
                no_change_option=option,
                competency_objective=(
                    "Identify applicable competencies from genuine occupation requirements "
                    "and reviewed curriculum passages."
                ),
                evidence_sufficiency="insufficient_evidence",
                priority="review_first",
                priority_basis="Missing reviewed mappings or requirements.",
                limitations=["insufficient_evidence", "no_title_based_competency_inference"],
                review_status="needs_evidence",
            )
        )
    return recommendations


def evaluate(
    session, programme_id, revision_id, request: CareerRequest, settings, as_of
) -> CareerResult:
    if as_of.tzinfo is None or as_of > datetime.now(UTC) + timedelta(seconds=1):
        _invalid("Career evidence cutoff must be aware and cannot be in the future")
    programme = session.get(Programme, programme_id)
    revision = session.get(ProgrammeRevision, revision_id)
    if programme is None or revision is None:
        raise DomainError("NOT_FOUND", "Programme or revision was not found", 404)
    if revision.programme_id != programme.id or (
        request.revision_id and request.revision_id != revision.id
    ):
        _invalid("Programme and career request revision do not agree")
    institution = session.get(Institution, programme.institution_id)
    courses = session.scalars(
        select(Course).where(Course.programme_revision_id == revision.id).order_by(Course.id)
    ).all()
    if len(courses) > 1000:
        _invalid("Career inventory exceeds the 1000-course limit")
    if institution is None or not all(
        row.is_synthetic == programme.is_synthetic for row in [institution, revision, *courses]
    ):
        _invalid("Programme, institution, revision and course evidence lanes do not agree")
    context = _Context(session, programme, revision, courses, settings, as_of)
    by_skill, gaps = defaultdict(list), defaultdict(list)
    for assertion in request.assertions:
        if assertion.course_id not in context.courses:
            _invalid("A competency assertion belongs to another course inventory")
        skill = session.get(Skill, assertion.skill_id)
        if skill is None:
            _invalid("The competency assertion has no registered skill identity")
        by_skill[skill.id].append(assertion)
    for gap in request.gaps:
        if session.get(Skill, gap.skill_id) is None:
            _invalid("The gap assertion has no registered skill identity")
        gaps[gap.skill_id].append(gap)
    alignments, all_requirements = [], []
    programme_discipline = discipline_for(programme.name, programme.discipline_key)
    for mapping in request.mappings:
        occupation = session.get(Occupation, mapping.occupation_id)
        if occupation is None:
            _invalid("The supplied occupation is not a registered source record")
        if occupation.taxonomy != mapping.taxonomy or occupation.external_id != mapping.external_id:
            _invalid("Occupation taxonomy and exact source identifier do not agree")
        if (
            discipline_for(mapping.discipline) != programme_discipline
            or programme_discipline == "unknown"
        ):
            _invalid("The reviewed occupation mapping is for a different programme discipline")
        occupation_item = context.record(occupation, "occupation", "occupation_benchmark")
        if occupation_item is None:
            continue
        requirements, complete = [], mapping.requirements_complete
        relations = session.scalars(
            select(OccupationSkill)
            .where(OccupationSkill.occupation_id == occupation.id)
            .order_by(OccupationSkill.id)
            .limit(MAX_REQUIREMENTS + 1)
        ).all()
        if not relations or len(relations) > MAX_REQUIREMENTS:
            complete = False
        for relation in relations[:MAX_REQUIREMENTS]:
            if len(all_requirements) + len(requirements) >= MAX_REQUIREMENTS:
                context.limitations.append("requirement_budget_exhausted")
                complete = False
                break
            skill = session.get(Skill, relation.skill_id)
            if (
                skill is None
                or skill.version_id != occupation.version_id
                or relation.version_id != occupation.version_id
                or skill.taxonomy != occupation.taxonomy
            ):
                complete = False
                context.limitations.append("skill_relationship_version_or_taxonomy_incomplete")
                continue
            skill_item = context.record(skill, "skill", "occupation_benchmark")
            relation_item = context.record(relation, "occupation_skill", "occupation_benchmark")
            if skill_item is None or relation_item is None:
                complete = False
                continue
            requirements.append(
                _requirement(
                    context,
                    mapping,
                    occupation,
                    relation,
                    skill,
                    [occupation_item, relation_item, skill_item],
                    by_skill[skill.id],
                    gaps[skill.id],
                )
            )
        current = (
            mapping.reviewed
            and mapping.reviewed_at <= as_of
            and all(
                _current(context.evidence[citation.reference_id])
                for value in requirements
                for citation in value.citations
            )
        )
        current = current and _current(occupation_item)
        occupation_item.facts.update(
            mapping_reviewed=bool(mapping.reviewed and mapping.reviewed_at <= as_of),
            requirements_complete=bool(complete),
            mapping_discipline=mapping.discipline,
        )
        measure = _measure(requirements, complete, current)
        status = _alignment_status(requirements, complete, current)
        workforce, ai = _context_signals(context, occupation)
        limitations = list(occupation_item.limitations) + [
            "programme_occupation_mapping_is_a_reviewed_inference_not_employment_matching",
            "taxonomy_does_not_establish_Malaysian_demand",
            "no_university_quality_or_graduate_proficiency_ranking",
        ]
        if not complete:
            limitations.append("occupation_requirement_completeness_not_established")
        if not workforce:
            limitations.append("no_eligible_exact_occupation_workforce_comparison")
        alignments.append(
            OccupationAlignment(
                occupation_id=occupation.id,
                occupation_name=occupation.label,
                taxonomy=occupation.taxonomy,
                external_id=occupation.external_id,
                version_id=occupation.version_id,
                description=occupation.description,
                mapping_basis=mapping.basis,
                malaysia_applicability=mapping.malaysia_applicability,
                status=status,
                requirements=requirements,
                measure=measure,
                workforce=workforce,
                ai_transformation=ai,
                citations=[_citation(occupation_item)],
                limitations=limitations,
            )
        )
        all_requirements.extend(requirements)
    status = _programme_status(alignments, context.limitations)
    limitations = [
        "Curriculum evidence describes bounded documented preparation, "
        "not individual employment probabilities or graduate competence.",
        "No course-title competency inference, invented skill requirement, "
        "automatic curriculum change or confirmed gap from absence of evidence.",
        "Academic approval and Domain 1 institutional-workflow waiver remain separate.",
    ] + context.limitations
    if not request.mappings:
        limitations.append(
            "No reviewed occupation mapping was supplied; "
            "candidate titles are not matched automatically."
        )
    if any(not course.detailed_syllabus_available for course in courses):
        limitations.append(
            "needs_syllabus_confirmation: title-only records cannot establish taught content."
        )
    if (
        "evidence_budget_exhausted" in context.limitations
        or "requirement_budget_exhausted" in context.limitations
    ):
        status = "insufficient_evidence"
        for alignment in alignments:
            alignment.measure.value = None
            alignment.measure.abstention_reason = "Evidence retrieval was truncated."
    result = CareerResult(
        programme_id=programme.id,
        programme_revision_id=revision.id,
        as_of=as_of,
        is_synthetic=programme.is_synthetic,
        status=status,
        occupations=alignments,
        competencies=all_requirements,
        recommendations=_recommendations(revision.id, all_requirements),
        evidence=list(context.evidence.values()),
        course_ids=[row.id for row in courses],
        limitations=list(dict.fromkeys(limitations)),
        permission_policy=context.permission_policy,
        model={"status": "deterministic", "request_count": 0, "observed_cost": None},
    )
    return validate_career_result(result)


def validate_career_result(result) -> CareerResult:
    """Validate frozen academic facts after deterministic or optional model reasoning."""
    result = CareerResult.model_validate(result)
    evidence = {row.id: row for row in result.evidence}
    if len(evidence) != len(result.evidence) or len(result.course_ids) != len(
        set(result.course_ids)
    ):
        raise ValueError("Career evidence or course identities are duplicated")
    for item in evidence.values():
        if (
            item.is_synthetic != result.is_synthetic
            or item.review_status == "rejected"
            or not item.internal_eligible
            or not item.rights.internal_analysis_allowed
            or not item.rights.excerpt_output_allowed
        ):
            raise ValueError(
                "Career evidence is not admitted in the correct permission/evidence lane"
            )
        if item.retrieved_at and item.retrieved_at > result.as_of:
            raise ValueError("Career evidence was not known at the frozen cutoff")

    def citations(rows):
        for citation in rows:
            item = evidence.get(citation.reference_id)
            if (
                item is None
                or not _normal(citation.quote)
                or _normal(citation.quote) not in _normal(item.excerpt)
            ):
                raise ValueError("Career citation quote does not match an admitted source")

    requirement_keys = set()
    for requirement in result.competencies:
        key = (requirement.occupation_id, requirement.relationship_id, requirement.skill_id)
        if key in requirement_keys:
            raise ValueError("Career requirement is duplicated")
        requirement_keys.add(key)
        citations(requirement.citations)
        references = [evidence[row.reference_id] for row in requirement.citations]
        relation = next(
            (
                row
                for row in references
                if row.kind == "occupation_skill" and row.record_id == requirement.relationship_id
            ),
            None,
        )
        skill = next(
            (
                row
                for row in references
                if row.kind == "skill" and row.record_id == requirement.skill_id
            ),
            None,
        )
        occupation = next(
            (
                row
                for row in references
                if row.kind == "occupation" and row.record_id == requirement.occupation_id
            ),
            None,
        )
        if (
            not all((relation, skill, occupation))
            or not (relation.version_id == skill.version_id == occupation.version_id)
            or relation.facts.get("occupation_id") != str(requirement.occupation_id)
            or relation.facts.get("skill_id") != str(requirement.skill_id)
        ):
            raise ValueError(
                "Career requirement has no matching source occupation/skill relationship"
            )
        if (
            relation.facts.get("relationship", "").casefold() != requirement.requirement_type
            and requirement.requirement_type != "unknown"
        ):
            raise ValueError("Career requirement changes the published relationship type")
        if requirement.skill_name != skill.facts.get("label"):
            raise ValueError("Career requirement changes its source skill name")
        for support in requirement.courses:
            if support.course_id not in result.course_ids:
                raise ValueError("Career support refers to an extra course")
            citations(support.citations)
            for citation in support.citations:
                item = evidence[citation.reference_id]
                if (
                    item.kind != "curriculum"
                    or item.facts.get("course_id") != str(support.course_id)
                    or item.facts.get("skill_id") != str(requirement.skill_id)
                    or item.version_id != result.programme_revision_id
                ):
                    raise ValueError("Career support cites a different skill/course/revision")
                if support.support != "unknown" and (
                    support.support != item.facts.get("support") or not _current(item)
                ):
                    raise ValueError("Career support changes its reviewed assertion type")
                if support.extent == "full" and (
                    item.facts.get("extent") != "full"
                    or item.facts.get("course_type") != CourseType.COMPULSORY
                ):
                    raise ValueError("Full programme coverage needs a full compulsory assertion")
            if support.support == "demonstrated" and not any(
                evidence[row.reference_id].facts.get("demonstration_reviewed") is True
                and _current(evidence[row.reference_id])
                for row in support.citations
            ):
                raise ValueError("Career demonstration has no reviewed assessed evidence")
        current_requirement = occupation.facts.get("mapping_reviewed") is True and all(
            _current(item) for item in (occupation, relation, skill)
        )
        if requirement.state != "unknown" and not current_requirement:
            raise ValueError("Career coverage requires a reviewed current requirement mapping")
        if requirement.state == "supported" and not (
            requirement.support_type == "demonstrated"
            and any(
                row.support == "demonstrated" and row.extent == "full"
                for row in requirement.courses
            )
        ):
            raise ValueError("Career supported coverage lacks a full demonstrated assertion")
        positive = [
            support
            for support in requirement.courses
            if support.support in {"demonstrated", "documented_intent"}
        ]
        if requirement.state == "partial" and (
            not positive or requirement.support_type not in {"demonstrated", "documented_intent"}
        ):
            raise ValueError("Career partial coverage lacks reviewed intended or assessed support")
        if requirement.state == "documented_gap":
            audits = [
                row
                for row in references
                if row.kind == "curriculum_gap"
                and row.facts.get("negative_audit_reviewed") is True
                and row.facts.get("skill_id") == str(requirement.skill_id)
                and set(row.facts.get("covered_course_ids", []))
                == {str(value) for value in result.course_ids}
                and _current(row)
            ]
            if not audits or any(
                row.support in {"demonstrated", "documented_intent"} for row in requirement.courses
            ):
                raise ValueError(
                    "Career documented gap lacks a complete nonconflicting reviewed audit"
                )
    occupation_ids = {row.occupation_id for row in result.occupations}
    if len(occupation_ids) != len(result.occupations):
        raise ValueError("Career occupations are duplicated")
    flattened = {}
    for alignment in result.occupations:
        citations(alignment.citations)
        source = next(
            (
                evidence[citation.reference_id]
                for citation in alignment.citations
                if evidence[citation.reference_id].kind == "occupation"
                and evidence[citation.reference_id].record_id == alignment.occupation_id
            ),
            None,
        )
        if (
            source is None
            or source.version_id != alignment.version_id
            or source.facts.get("taxonomy") != alignment.taxonomy
            or source.facts.get("external_id") != alignment.external_id
            or source.facts.get("label") != alignment.occupation_name
        ):
            raise ValueError("Career occupation changes its source identity or name")
        for requirement in alignment.requirements:
            flattened[
                (requirement.occupation_id, requirement.relationship_id, requirement.skill_id)
            ] = requirement
            if requirement.occupation_id != alignment.occupation_id:
                raise ValueError("Career occupation contains a different occupation's requirement")
        measure = alignment.measure
        current = (
            source.facts.get("mapping_reviewed") is True
            and _current(source)
            and all(
                _current(evidence[citation.reference_id])
                for requirement in alignment.requirements
                for citation in requirement.citations
            )
        )
        expected_status = _alignment_status(
            alignment.requirements,
            source.facts.get("requirements_complete") is True,
            current,
        )
        if alignment.status != expected_status:
            raise ValueError("Career alignment status changes its deterministic coverage state")
        expected = _measure(
            alignment.requirements,
            source.facts.get("requirements_complete") is True,
            current,
        )
        if (
            measure.numerator != expected.numerator
            or measure.denominator != expected.denominator
            or measure.assessed_requirements != expected.assessed_requirements
            or measure.unknown_requirements != expected.unknown_requirements
            or measure.weights != {"essential": 1.0}
        ):
            raise ValueError("Career score metadata changes the declared requirement denominator")
        if measure.value is not None:
            if (
                expected.value is None
                or measure.value != expected.value
                or measure.abstention_reason is not None
            ):
                raise ValueError(
                    "Career score changes the declared deterministic essential-requirement method"
                )
    if set(flattened) != requirement_keys or any(
        flattened[(row.occupation_id, row.relationship_id, row.skill_id)] != row
        for row in result.competencies
    ):
        raise ValueError("Career programme and occupation requirement matrices disagree")
    if result.status != _programme_status(result.occupations, result.limitations):
        raise ValueError("Career programme status changes its deterministic coverage state")
    for recommendation in result.recommendations:
        citations(recommendation.citations)
        if (
            recommendation.programme_revision_id != result.programme_revision_id
            or not set(recommendation.course_ids) <= set(result.course_ids)
            or not set(recommendation.occupation_ids) <= occupation_ids
        ):
            raise ValueError("Career recommendation crosses programme/course/occupation scope")
        if (
            recommendation.evidence_sufficiency != "insufficient_evidence"
            and not recommendation.citations
        ):
            raise ValueError("Career recommendation lacks source support")
        if recommendation.no_change_option.category != "no_change":
            raise ValueError("Career recommendation must preserve a genuine no-change option")
        if recommendation.skill_id is not None and recommendation.skill_id not in {
            requirement.skill_id for requirement in result.competencies
        }:
            raise ValueError("Career recommendation invents an unsupported competency")
        if recommendation.evidence_sufficiency == "insufficient_evidence" and (
            recommendation.category not in {"request_review", "no_change"}
            or recommendation.priority == "supported_need"
        ):
            raise ValueError(
                "Insufficient career evidence cannot justify a substantive intervention"
            )
    canonical = _recommendations(result.programme_revision_id, result.competencies)
    if [row.model_dump(mode="json") for row in result.recommendations] != [
        row.model_dump(mode="json") for row in canonical
    ]:
        raise ValueError("Career recommendations change the deterministic eligible interventions")
    return result
