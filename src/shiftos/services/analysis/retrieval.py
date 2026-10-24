"""Bounded internal evidence selection. Lexical relevance is never an identity bridge."""

import calendar
import hashlib
import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from shiftos.core.enums import DocumentKind
from shiftos.core.errors import DomainError
from shiftos.models import (
    AcademicStandard,
    AIImpactEvidence,
    Course,
    Dataset,
    DatasetVersion,
    Document,
    DocumentAnchor,
    EvidenceReference,
    Occupation,
    OccupationalTask,
    OccupationSkill,
    Programme,
    ProgrammeRevision,
    Skill,
    Source,
    WorkforceObservation,
)
from shiftos.schemas.analysis import CourseEvidence, EvidenceItem, EvidencePacket, RightsDecision
from shiftos.services.evidence.trends import compare_observations

MAX_RECORDS_PER_FAMILY = 2000
MAX_REFERENCES = 300
MAX_EXCERPT = 1800
DISCIPLINES = {
    "accounting": {"accounting", "accountancy", "accountant"},
    "biotechnology": {"biotechnology", "biotech", "marine biotechnology"},
    "chemistry": {"chemistry", "chemical science"},
    "computing": {
        "computing",
        "computer science",
        "software engineering",
        "data science",
        "information technology",
        "information system",
        "cyber security",
        "cybersecurity",
    },
    "engineering": {"engineering", "electronic", "electrical", "mechatronic", "robotics"},
    "finance": {"finance", "financial", "banking"},
    "business": {"business", "management", "economics", "marketing", "commerce"},
    "media": {"media", "communication", "journalism", "advertising"},
    "languages": {"language", "linguistic", "literature", "chinese studies", "translation"},
    "mathematics": {"mathematics", "mathematical", "statistics", "actuarial"},
    "physics": {"physics", "physical science"},
    "hospitality": {"hospitality", "tourism", "hotel"},
    "traditional_medicine": {"traditional chinese medicine", "complementary medicine"},
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "bachelor",
    "honours",
    "synthetic",
    "test",
    "fictional",
    "study",
    "studies",
    "introduction",
    "introductory",
    "advanced",
    "basic",
    "principles",
    "course",
    "courses",
    "i",
    "ii",
    "iii",
    "iv",
}
GENERIC = {"data", "analysis", "system", "management", "research", "science", "method", "skill"}


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def freeze_packet(packet: EvidencePacket) -> EvidencePacket:
    packet.manifest_hash = fingerprint(packet.model_dump(mode="json", exclude={"manifest_hash"}))
    return packet


def discipline_for(name: str, key: str | None = None) -> str:
    """Recognise explicit programme labels only; do not default an unknown major to computing."""
    for candidate in (key or "", name):
        normal = re.sub(r"[_-]+", " ", candidate.casefold())
        # Specific fields precede broad management/engineering terms.
        for discipline, labels in DISCIPLINES.items():
            if any(
                re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", normal) for label in labels
            ):
                return discipline
    return "unknown"


def _terms(value: str) -> set[str]:
    result = set()
    for token in re.findall(r"[^\W\d_]+", value.casefold(), re.UNICODE):
        if token in STOP_WORDS or len(token) < 3:
            continue
        if token.endswith("ies"):
            token = token[:-3] + "y"
        elif token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        token = {"accountant": "accounting", "accountancy": "accounting"}.get(token, token)
        result.add(token)
    return result


def _date_interval(label: str | None) -> tuple[date | None, date | None, str]:
    if not label:
        return None, None, "unknown"
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", label):
            day = date.fromisoformat(label)
            return day, day, "day"
        if re.fullmatch(r"\d{4}-\d{2}", label):
            year, month = map(int, label.split("-"))
            return (
                date(year, month, 1),
                date(year, month, calendar.monthrange(year, month)[1]),
                "month",
            )
        if re.fullmatch(r"\d{4}", label):
            return date(int(label), 1, 1), date(int(label), 12, 31), "year"
    except ValueError:
        pass
    return None, None, "unknown"


def _permission_layers(
    row, version: DatasetVersion, supplied: dict, reference: EvidenceReference | None
) -> list[dict]:
    layers = [supplied]
    metadata = version.metadata_json or {}
    for layer in (
        metadata,
        metadata.get("extraction", {}),
        metadata.get("transform", {}),
        row.metadata_json or {},
        (reference.metadata_json or {}) if reference is not None else {},
    ):
        if isinstance(layer, dict):
            permission = layer.get("analysis_permissions")
            if isinstance(permission, dict):
                layers.append(permission)
            if layer.get("rights_withdrawn") is True:
                layers.append(
                    {
                        "internal_analysis_allowed": False,
                        "external_model_allowed": False,
                        "excerpt_output_allowed": False,
                        "basis": "Rights withdrawn",
                    }
                )
    return layers


def _rights(
    row,
    version: DatasetVersion,
    policy: dict,
    synthetic: bool,
    reference: EvidenceReference | None = None,
) -> RightsDecision:
    layers = _permission_layers(row, version, policy, reference)
    if synthetic:
        layers.insert(
            0,
            {
                "internal_analysis_allowed": True,
                "external_model_allowed": True,
                "excerpt_output_allowed": True,
                "basis": "Explicit synthetic fixture lane",
            },
        )
    flags = {}
    for flag in ("internal_analysis_allowed", "external_model_allowed", "excerpt_output_allowed"):
        values = [layer[flag] for layer in layers if isinstance(layer.get(flag), bool)]
        flags[flag] = bool(values) and True in values and False not in values
    bases = [
        layer["basis"]
        for layer in layers
        if isinstance(layer.get("basis"), str) and layer["basis"].strip()
    ]
    if not bases:
        flags = dict.fromkeys(flags, False)
    return RightsDecision(
        **flags, basis="; ".join(bases)[:1500] or "No explicit processing/reuse policy recorded"
    )


def _relevant(text: str, course_terms: set[str]) -> list[str]:
    common = _terms(text) & course_terms
    if len(common) >= 2 or any(len(term) >= 6 and term not in GENERIC for term in common):
        return sorted(common)
    return []


def _public_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url)
        return (
            url
            if parts.scheme == "https"
            and parts.hostname
            and not parts.username
            and not parts.password
            and not any(
                key.casefold() in {"token", "api_key", "apikey", "access_token", "key", "secret"}
                for key, _ in parse_qsl(parts.query)
            )
            else None
        )
    except ValueError:
        return None


def retrieve_evidence(
    session: Session,
    programme_revision_id: UUID,
    as_of: datetime,
    *,
    permitted_sources: dict[str, dict] | None = None,
) -> EvidencePacket:
    """Freeze permitted minimal evidence, with every course and explicit missing evidence.

    Source text denied external processing is never placed in this model-facing
    packet, even when it may be used for internal matching. No network calls or
    generated translations/classification crosswalks occur here.
    """
    if as_of.tzinfo is None or as_of > datetime.now(UTC) + timedelta(seconds=1):
        raise ValueError("Evidence cutoff must be aware and not in the future")
    revision = session.get(ProgrammeRevision, programme_revision_id)
    if revision is None:
        raise DomainError("NOT_FOUND", "Programme revision not found", 404)
    programme = session.get(Programme, revision.programme_id)
    policy = permitted_sources or {}
    rows = session.scalars(
        select(Course).where(Course.programme_revision_id == revision.id).order_by(Course.id)
    ).all()
    if len(rows) > 1000:
        raise DomainError("ANALYSIS_LIMIT", "Inventory exceeds the 1000-course analysis limit", 422)
    synthetic = programme.is_synthetic
    if revision.is_synthetic != synthetic or any(row.is_synthetic != synthetic for row in rows):
        raise ValueError("Inconsistent synthetic curriculum lineage")
    discipline = discipline_for(programme.name, programme.discipline_key)
    courses = [
        CourseEvidence(
            id=row.id,
            name=row.course_name,
            year=row.year,
            course_type=str(row.course_type),
            evidence_level="title_only",
            is_verified=row.is_verified,
            needs_syllabus_confirmation=True,
            source_id=row.source_id,
            source_url=_public_url(row.source_url),
            source_locator=row.source_locator,
            limitations=[
                "Title inventory does not establish taught content "
                "or complete graduation requirements"
            ],
        )
        for row in rows
    ]
    terms = {course.id: _terms(course.name) for course in courses}
    gaps = set()
    if discipline == "unknown":
        gaps.add("unknown_discipline")
    if not courses:
        gaps.add("empty_inventory")
    if courses:
        gaps.add("syllabus_confirmation_required")
    packet = EvidencePacket(
        programme_id=programme.id,
        programme_revision_id=revision.id,
        institution_id=programme.institution_id,
        programme_name=programme.name,
        discipline=discipline,
        is_synthetic=synthetic,
        as_of=as_of,
        source_policy_hash=fingerprint(policy),
        courses=courses,
        limitations=[
            "Lexical course associations are review candidates, "
            "not taught-content or occupation identities",
            "Engineering/source review is not independent academic approval",
            "Frozen bounded evidence does not certify complete curriculum or discipline coverage",
        ],
    )
    occupations, occupation_reviews = _bounded_identities(
        session, Occupation, synthetic, as_of, packet, policy
    )
    skills, _ = _bounded_identities(session, Skill, synthetic, as_of, packet, policy)
    workforce: list[WorkforceObservation] = []
    admitted_kinds = set()
    families = [
        (AcademicStandard, "academic_standard", "academic_benchmark", "published_standard"),
        (Occupation, "occupation", "occupation_benchmark", "occupation_requirement"),
        (Skill, "skill", "occupation_benchmark", "occupation_requirement"),
        (OccupationSkill, "occupation_skill", "occupation_benchmark", "occupation_requirement"),
        (OccupationalTask, "task", "occupation_benchmark", "occupation_requirement"),
        (AIImpactEvidence, "ai_evidence", "ai_task_context", "dated_ai_capability"),
        (WorkforceObservation, "workforce", "workforce_context", "dated_workforce_signal"),
    ]
    for model, kind, scope, expected in families:
        candidates = session.execute(_candidate_query(model, synthetic, as_of)).all()
        if len(candidates) > MAX_RECORDS_PER_FAMILY:
            packet.truncated = True
        for row, reference, version, source, dataset in candidates[:MAX_RECORDS_PER_FAMILY]:
            if (
                version.retrieved_at > as_of
                or (source.published_at and source.published_at > as_of)
                or (source.collected_at and source.collected_at > as_of)
            ):
                continue
            if not all(
                item.is_synthetic == synthetic for item in (row, reference, version, source)
            ):
                continue
            earliest, latest, precision = _date_interval(version.publication_date)
            if earliest and earliest > as_of.date():
                continue
            if kind == "workforce" and row.period_end > as_of.date():
                continue
            metadata = row.metadata_json or {}
            text = " ".join(
                str(getattr(row, key, "") or "")
                for key in (
                    "label",
                    "description",
                    "discipline",
                    "title",
                    "statement",
                    "occupation_label",
                    "task",
                    "capability",
                )
            )
            if kind == "occupation_skill":
                occupation, skill = occupations.get(row.occupation_id), skills.get(row.skill_id)
                if not occupation or not skill:
                    continue
                text = f"{occupation.label} {skill.label} {skill.description or ''}"
            associations = {course.id: _relevant(text, terms[course.id]) for course in courses}
            standard_match = (
                kind == "academic_standard"
                and discipline != "unknown"
                and discipline_for(row.discipline) == discipline
            )
            related = metadata.get("related_disciplines", [])
            related = related if isinstance(related, list) else []
            domain_match = discipline != "unknown" and (
                discipline_for(text) == discipline
                or any(discipline_for(str(label)) == discipline for label in related)
            )
            broad_workforce = (
                kind == "workforce"
                and row.geography == "MY"
                and (version.metadata_json or {}).get("transform", {}).get("adapter") == "dosm_jmi"
            )
            if not (
                standard_match or domain_match or broad_workforce or any(associations.values())
            ):
                continue
            # A shared word cannot make a different discipline's programme standard applicable.
            if kind == "academic_standard" and not standard_match:
                continue
            if len(packet.references) >= MAX_REFERENCES:
                packet.truncated = True
                continue
            rights = _rights(
                row, version, policy.get(dataset.registry_key, {}), synthetic, reference
            )
            reasons = []
            if any(
                container.get("extraction_candidate")
                for container in (metadata, reference.metadata_json or {})
            ):
                reasons.append("unverified_pdf_extraction_candidate")
            if reference.review_status == "rejected":
                reasons.append("rejected_reference")
            if any(
                metadata.get(key) is True or (version.metadata_json or {}).get(key) is True
                for key in ("retracted", "superseded", "correction_pending")
            ):
                reasons.append("correction_or_retraction_requires_review")
                gaps.add("currentness_review_required")
            expected_class = "synthetic_demo" if synthetic else expected
            actual_class = str(source.evidence_class)
            if actual_class != expected_class and not (
                kind == "ai_evidence"
                and row.impact_type == "occupational_exposure"
                and actual_class == "dated_workforce_signal"
            ):
                reasons.append("incompatible_evidence_class")
            if not _public_url(source.url) and not synthetic:
                reasons.append("missing_safe_source_url")
            if not rights.internal_analysis_allowed:
                reasons.append("internal_use_not_approved")
            if not rights.external_model_allowed or not rights.excerpt_output_allowed:
                gaps.add("rights_review_required")
            internal_eligible = not reasons
            model_eligible = (
                internal_eligible
                and rights.external_model_allowed
                and rights.excerpt_output_allowed
            )
            temporal = precision != "day"
            if precision == "unknown":
                gaps.add("missing_source_dates")
            max_age = {
                "ai_evidence": 730,
                "workforce": 550,
                "occupation": 1825,
                "skill": 1825,
                "occupation_skill": 1825,
                "task": 1825,
            }.get(kind)
            if earliest and max_age and (as_of.date() - earliest).days > max_age:
                temporal = True
                gaps.add("currentness_review_required")
            facts = {}
            identity = False
            local_scope = scope
            if kind == "academic_standard":
                facts = {
                    "discipline": row.discipline,
                    "qualification_level": metadata.get("mqf_level"),
                    "benchmark_only": True,
                }
                bachelor = bool(
                    re.search(r"\bbachelor\b", programme.name.casefold())
                    or (programme.level or "").casefold() in {"bachelor", "bachelors", "mqf6", "6"}
                )
                if metadata.get("mqf_level") not in (6, "6") or not bachelor:
                    reasons.append("qualification_applicability_unconfirmed")
                    gaps.add("missing_standards")
            elif kind in {"occupation", "skill"}:
                facts = {
                    "external_id": row.external_id,
                    "label": row.label,
                    "taxonomy": row.taxonomy,
                }
            elif kind == "occupation_skill":
                facts = {
                    "occupation_id": str(row.occupation_id),
                    "skill_id": str(row.skill_id),
                    "relationship": row.relationship,
                }
            elif kind == "ai_evidence":
                local_scope = (
                    "ai_exposure_context"
                    if row.impact_type in {"occupational_exposure", "future_prediction"}
                    else "ai_task_context"
                )
                occupation = occupations.get(row.occupation_id)
                if occupation is not None:
                    identity = occupation.id in occupation_reviews
                if not identity and metadata.get("occupation_match_reviewed") is True:
                    identity = any(
                        metadata.get("occupation_taxonomy") == item.taxonomy
                        and metadata.get("occupation_external_id") == item.external_id
                        and item.id in occupation_reviews
                        for item in occupations.values()
                    )
                identity = (
                    identity
                    and reference.review_status == "reviewed"
                    and bool(row.task and row.capability)
                    and row.impact_type in {"observed_capability", "observed_practice"}
                    and not temporal
                )
                if not identity:
                    gaps.add("classification_bridge_unreviewed")
                facts = {
                    "impact_type": row.impact_type,
                    "occupation_label": row.occupation_label,
                    "identity_reviewed": identity,
                }
            elif kind == "workforce":
                facts = {
                    "indicator": row.indicator,
                    "value": str(row.value) if row.value is not None else None,
                    "unit": row.unit,
                    "geography": row.geography,
                    "population_level": "occupation_group"
                    if broad_workforce
                    else metadata.get("population_level", "unknown"),
                    "occupation_id": str(row.occupation_id) if row.occupation_id else None,
                }
            internal_eligible = not reasons
            model_eligible = (
                internal_eligible
                and rights.external_model_allowed
                and rights.excerpt_output_allowed
            )
            item = EvidenceItem(
                id=f"{kind}:{row.id}",
                kind=kind,
                record_id=row.id,
                version_id=version.id,
                evidence_reference_id=reference.id,
                source_id=source.id,
                dataset_key=dataset.registry_key,
                evidence_class=actual_class,
                scope=local_scope,
                source_url=_public_url(source.url),
                publisher=source.publisher,
                title=source.title,
                locator=reference.locator,
                excerpt=reference.excerpt[:MAX_EXCERPT] if model_eligible else "",
                publication_date=version.publication_date,
                date_precision=precision,
                observation_start=str(row.period_start) if kind == "workforce" else None,
                observation_end=str(row.period_end) if kind == "workforce" else None,
                study_period=row.study_period if kind == "ai_evidence" and model_eligible else None,
                model_version=str(metadata["model"])[:200]
                if metadata.get("model") and model_eligible
                else None,
                language=(metadata.get("language") or metadata.get("source_language"))
                if isinstance(metadata.get("language") or metadata.get("source_language"), str)
                else None,
                retrieved_at=version.retrieved_at,
                review_status=reference.review_status,
                is_synthetic=synthetic,
                rights=rights,
                internal_eligible=internal_eligible,
                model_eligible=model_eligible and not reasons,
                historical_context_only=temporal,
                identity_reviewed=identity,
                facts=facts if model_eligible else {},
                relevance_basis=["explicit_programme_discipline_benchmark"]
                if standard_match
                else ["broad_Malaysian_group_context_only"]
                if broad_workforce
                else ["lexical_candidate_not_identity"],
                limitations=(
                    ["Structured source assertion retains needs_review"]
                    if reference.review_status == "needs_review"
                    else []
                )
                + (
                    ["Dated historical context only; not current capability/demand assurance"]
                    if temporal
                    else []
                ),
                exclusion_reasons=reasons,
            )
            if len(reference.excerpt) > MAX_EXCERPT:
                item.limitations.append("Evidence excerpt truncated to a bounded prefix")
                packet.truncated = True
            packet.references.append(item)
            if item.internal_eligible:
                admitted_kinds.add(kind)
            for course in courses:
                if standard_match or broad_workforce or associations[course.id] or domain_match:
                    course.reference_ids.append(item.id)
                    course.matching_terms = sorted(
                        set(course.matching_terms) | set(associations[course.id])
                    )
            if kind == "workforce" and item.model_eligible and not temporal:
                workforce.append(row)
    _syllabus_references(session, packet, rows, as_of)
    gaps.update(_radar(session, packet, workforce))
    for family, required in (
        ("occupations", "occupation"),
        ("skills", "skill"),
        ("standards", "academic_standard"),
        ("workforce", "workforce"),
        ("ai", "ai_evidence"),
    ):
        if required not in admitted_kinds:
            gaps.add(f"missing_{family}")
    if packet.truncated:
        gaps.add("retrieval_truncated")
    if all(not course.needs_syllabus_confirmation for course in packet.courses) and packet.courses:
        gaps.discard("syllabus_confirmation_required")
    packet.gaps = sorted(gaps)
    return freeze_packet(packet)


def _candidate_query(model, synthetic, as_of):
    """One bounded join per family; no source/version/reference query per record."""
    return (
        select(model, EvidenceReference, DatasetVersion, Source, Dataset)
        .join(
            EvidenceReference,
            (model.evidence_id == EvidenceReference.id)
            & (model.version_id == EvidenceReference.version_id),
        )
        .join(DatasetVersion, model.version_id == DatasetVersion.id)
        .join(Source, DatasetVersion.source_id == Source.id)
        .join(Dataset, DatasetVersion.dataset_id == Dataset.id)
        .where(
            model.is_synthetic == synthetic,
            DatasetVersion.is_synthetic == synthetic,
            EvidenceReference.is_synthetic == synthetic,
            Source.is_synthetic == synthetic,
            DatasetVersion.retrieved_at <= as_of,
        )
        .order_by(model.external_id, model.id)
        .limit(MAX_RECORDS_PER_FAMILY + 1)
    )


def _bounded_identities(session, model, synthetic, as_of, packet, policy):
    candidates = session.execute(_candidate_query(model, synthetic, as_of)).all()
    if len(candidates) > MAX_RECORDS_PER_FAMILY:
        packet.truncated = True
    admitted, reviewed = {}, set()
    for row, reference, version, source, dataset in candidates[:MAX_RECORDS_PER_FAMILY]:
        earliest, _, precision = _date_interval(version.publication_date)
        if (
            (source.published_at and source.published_at > as_of)
            or (source.collected_at and source.collected_at > as_of)
            or (earliest and earliest > as_of.date())
            or reference.review_status == "rejected"
            or any(
                container.get(key)
                for container in (
                    row.metadata_json or {},
                    reference.metadata_json or {},
                    version.metadata_json or {},
                )
                for key in ("extraction_candidate", "retracted", "superseded", "correction_pending")
            )
            or str(source.evidence_class)
            != ("synthetic_demo" if synthetic else "occupation_requirement")
            or not _rights(
                row, version, policy.get(dataset.registry_key, {}), synthetic, reference
            ).internal_analysis_allowed
        ):
            continue
        admitted[row.id] = row
        if (
            reference.review_status == "reviewed"
            and precision == "day"
            and earliest
            and (as_of.date() - earliest).days <= 1825
        ):
            reviewed.add(row.id)
    return admitted, reviewed


def _syllabus_references(
    session: Session, packet: EvidencePacket, rows: list[Course], as_of: datetime
) -> None:
    """Only explicitly reviewed linked syllabus anchors may establish content evidence."""
    if not any(row.detailed_syllabus_available for row in rows):
        return
    courses = {course.id: course for course in packet.courses}
    candidates = session.execute(
        select(Document, DocumentAnchor, Course, Source)
        .join(DocumentAnchor, DocumentAnchor.document_id == Document.id)
        .join(
            Course,
            (Document.course_id == Course.id)
            & (Document.programme_revision_id == Course.programme_revision_id),
        )
        .join(Source, Course.source_id == Source.id)
        .where(
            Document.programme_revision_id == packet.programme_revision_id,
            Document.document_kind == DocumentKind.SYLLABUS,
            Document.uploaded_at <= as_of,
            Course.detailed_syllabus_available.is_(True),
        )
        .order_by(Course.id, Document.id, DocumentAnchor.id)
        .limit(10_001)
    ).all()
    if len(candidates) > 10_000:
        packet.truncated = True
    counts = {}
    for document, anchor, original, source in candidates[:10_000]:
        course = courses[original.id]
        metadata = document.metadata_json or {}
        if (
            metadata.get("content_reviewed") is not True
            or metadata.get("rights_withdrawn") is True
            or metadata.get("extraction_candidate")
        ):
            continue
        if (
            not all(
                item.is_synthetic == packet.is_synthetic
                for item in (source, document, anchor, original)
            )
            or (
                not packet.is_synthetic
                and (
                    not original.is_verified
                    or str(source.evidence_class) != "verified_university_fact"
                    or not _public_url(source.url)
                )
            )
            or (source.published_at and source.published_at > as_of)
            or (source.collected_at and source.collected_at > as_of)
        ):
            continue
        permission = metadata.get("analysis_permissions", {})
        if not isinstance(permission, dict) or any(
            permission.get(key) is False
            for key in (
                "internal_analysis_allowed",
                "external_model_allowed",
                "excerpt_output_allowed",
            )
        ):
            continue
        if not packet.is_synthetic and (
            not all(
                permission.get(key) is True
                for key in (
                    "internal_analysis_allowed",
                    "external_model_allowed",
                    "excerpt_output_allowed",
                )
            )
            or not isinstance(permission.get("basis"), str)
            or not permission["basis"].strip()
        ):
            continue
        if counts.get(course.id, 0) >= 10 or len(packet.references) >= MAX_REFERENCES:
            packet.truncated = True
            continue
        counts[course.id] = counts.get(course.id, 0) + 1
        item = EvidenceItem(
            id=f"syllabus:{anchor.id}",
            kind="syllabus",
            record_id=anchor.id,
            version_id=packet.programme_revision_id,
            evidence_reference_id=anchor.id,
            source_id=source.id,
            evidence_class=str(source.evidence_class),
            scope="verified_syllabus",
            source_url=_public_url(source.url),
            publisher=source.publisher,
            title=source.title,
            locator=anchor.locator,
            excerpt=anchor.excerpt[:MAX_EXCERPT],
            retrieved_at=document.uploaded_at,
            review_status="reviewed",
            is_synthetic=packet.is_synthetic,
            rights=RightsDecision(
                internal_analysis_allowed=True,
                external_model_allowed=True,
                excerpt_output_allowed=True,
                basis=permission.get("basis", "Explicit synthetic fixture content review"),
            ),
            internal_eligible=True,
            model_eligible=True,
            relevance_basis=["explicit_reviewed_course_document_link"],
        )
        if len(anchor.excerpt) > MAX_EXCERPT:
            item.limitations.append("Evidence excerpt truncated to a bounded prefix")
            packet.truncated = True
        packet.references.append(item)
        course.reference_ids.append(item.id)
        course.evidence_level = "detailed_syllabus"
        course.needs_syllabus_confirmation = False


def _radar(session: Session, packet: EvidencePacket, rows: list[WorkforceObservation]) -> set[str]:
    gaps = set()
    series: dict[tuple, list] = {}
    for row in rows:
        key = (
            row.occupation_label,
            row.sector,
            row.geography,
            row.indicator,
            row.unit,
            row.classification_system,
            row.classification_code,
            fingerprint(row.metadata_json or {}),
        )
        # Raw published values can vary while population/method metadata remains constant.
        metadata = {
            k: v for k, v in (row.metadata_json or {}).items() if k not in {"raw_value", "raw"}
        }
        key = key[:-1] + (fingerprint(metadata),)
        series.setdefault(key, []).append(row)
    if len(series) > 20:
        packet.truncated = True
    for values in list(series.values())[:20]:
        by_period = {}
        conflicts = False
        for row in sorted(values, key=lambda row: (row.period_start, str(row.id))):
            previous = by_period.get((row.period_start, row.period_end))
            if previous and (previous.value, previous.value_status) != (
                row.value,
                row.value_status,
            ):
                conflicts = True
            by_period[(row.period_start, row.period_end)] = row
        if conflicts:
            gaps.add("workforce_observations_conflict")
            continue
        ordered = list(by_period.values())
        if len(ordered) < 2:
            continue
        result = compare_observations(session, ordered[-2].id, ordered[-1].id)
        # Do not forward full raw radar inputs or unfiltered AI records to an external model.
        packet.radar.append(
            {
                "before_reference_id": f"workforce:{ordered[-2].id}",
                "after_reference_id": f"workforce:{ordered[-1].id}",
                "classification": result.classification,
                "absolute_change": str(result.absolute_change)
                if result.absolute_change is not None
                else None,
                "percentage_change": str(result.percentage_change)
                if result.percentage_change is not None
                else None,
                "population_level": result.population_level,
                "measurement_kind": result.measurement_kind,
                "time_horizon": result.time_horizon,
                "compatible": result.compatible,
                "policy": result.policy.model_dump(mode="json"),
                "fingerprint": result.fingerprint,
                "limitations": result.limitations,
            }
        )
    return gaps
