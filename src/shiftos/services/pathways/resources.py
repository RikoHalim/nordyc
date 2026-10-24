"""Reviewed original resources; availability, costs and effort are never guessed."""

import ipaddress
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import AwareDatetime, Field

from shiftos.core.errors import DomainError
from shiftos.models import Dataset, DatasetVersion, EvidenceReference, Source
from shiftos.schemas.analysis import EvidenceItem, StrictModel
from shiftos.schemas.career import CareerCitation
from shiftos.schemas.pathways import DurationEstimate, Hours, LearningResource
from shiftos.services.analysis.orchestrator import _permissions
from shiftos.services.analysis.retrieval import _date_interval, _public_url, _rights


class ResourceFacts(StrictModel):
    name: str = Field(min_length=1, max_length=500)
    resource_type: str = Field(min_length=1, max_length=100)
    url: str = Field(max_length=2000)
    related_skill_ids: list[UUID] = Field(min_length=1, max_length=100)
    prerequisite_skill_ids: list[UUID] = Field(default_factory=list, max_length=100)
    access_status: str
    cost_status: str
    cost_amount: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    cost_currency: str | None = Field(default=None, max_length=10)
    verified_at: AwareDatetime
    cost_verified_at: AwareDatetime | None = None
    licence_limitations: str = Field(min_length=1, max_length=2000)
    duration_hours: Hours | None = None
    duration_component: str = "learning"


def invalid(message):
    raise DomainError("ACTION_PLAN_INPUT_INVALID", message, 422)


def safe_url(value):
    if not _public_url(value):
        return False
    host = urlsplit(value).hostname.lower()
    if host == "localhost" or host.endswith((".local", ".localhost")):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return "." in host


def _resource(item):
    if (
        item.evidence_class == "inference"
        or (item.evidence_class == "synthetic_demo") != item.is_synthetic
    ):
        invalid("An inference is not a verified original learning resource")
    facts = ResourceFacts.model_validate(item.facts["learning_resource"])
    cutoff = datetime.fromisoformat(item.facts["as_of"])
    if not safe_url(facts.url) or facts.url != item.source_url:
        invalid("Resource original URL is unsafe or inconsistent")
    if facts.verified_at > cutoff or facts.duration_component not in {
        "learning",
        "contact",
        "assessment",
    }:
        invalid("Resource verification or duration component is invalid")
    if facts.cost_status not in {"free", "paid", "unknown"} or facts.access_status not in {
        "open",
        "restricted",
        "unknown",
    }:
        invalid("Resource access/cost status is invalid")
    if facts.cost_status == "unknown" and (
        facts.cost_amount is not None or facts.cost_currency is not None
    ):
        invalid("Unknown cost must not imply a price")
    if facts.cost_status == "free" and facts.cost_amount not in {None, Decimal(0)}:
        invalid("A free resource cannot have a nonzero cost")
    if facts.cost_status == "paid" and facts.cost_amount is not None and facts.cost_amount <= 0:
        invalid("Paid resource amount must be positive when known")
    if facts.cost_status != "unknown" and (
        facts.cost_verified_at is None or facts.cost_verified_at > cutoff
    ):
        invalid("Known cost requires dated original-source verification")
    if facts.cost_amount is not None and facts.cost_status == "paid" and not facts.cost_currency:
        invalid("A numeric price requires its currency")
    skill = UUID(item.facts["skill_id"])
    if skill not in facts.related_skill_ids:
        invalid("Resource does not establish the selected skill relationship")
    return LearningResource(
        key=f"resource:{item.record_id}:{skill}",
        reference_id=item.id,
        skill_id=skill,
        name=facts.name,
        publisher=item.publisher,
        url=facts.url,
        resource_type=facts.resource_type,
        access_status=facts.access_status,
        cost_status=facts.cost_status,
        cost_amount=facts.cost_amount,
        cost_currency=facts.cost_currency,
        publication_date=item.publication_date,
        verified_at=facts.verified_at,
        verification_status="synthetic_demo" if item.is_synthetic else "reviewed_original",
        licence_limitations=facts.licence_limitations,
        citations=[CareerCitation(reference_id=item.id, quote=item.excerpt)],
        limitations=[
            "Proposed resource; availability and academic suitability require review.",
            "Open access does not establish zero cost or achieved competence.",
        ],
    )


def admit_resources(session, bindings, career, settings, as_of):
    permissions, _ = _permissions(settings)
    skills = {str(row.skill_id) for row in career.competencies if row.skill_id is not None}
    resources, evidence, limitations = [], [], []
    seen = set()
    for binding in bindings:
        if binding.reference_id in seen:
            invalid("A resource reference can be admitted only once")
        seen.add(binding.reference_id)
        if str(binding.skill_id) not in skills:
            invalid("Resource skill is outside the parent career requirements")
        if not binding.reviewed or binding.reviewed_at > as_of:
            limitations.append("resource_relationship_not_reviewed_at_cutoff")
            continue
        reference = session.get(EvidenceReference, binding.reference_id)
        version = session.get(DatasetVersion, reference.version_id) if reference else None
        source = session.get(Source, version.source_id) if version else None
        dataset = session.get(Dataset, version.dataset_id) if version else None
        if not all((reference, version, source, dataset)):
            invalid("Resource has incomplete original-source lineage")
        synthetic = source.is_synthetic
        if str(source.evidence_class) == "inference":
            limitations.append("resource_inference_is_not_original_verification")
            continue
        if any(row.is_synthetic != synthetic for row in (reference, version, dataset)):
            invalid("Resource source lineage has inconsistent synthetic labels")
        if synthetic and not career.is_synthetic:
            invalid("Synthetic resources cannot substantiate a real programme plan")
        if (
            reference.review_status != "reviewed"
            or version.retrieved_at > as_of
            or (source.collected_at and source.collected_at > as_of)
            or (source.published_at and source.published_at > as_of)
        ):
            limitations.append("resource_original_not_reviewed_at_cutoff")
            continue
        containers = (reference.metadata_json or {}, version.metadata_json or {})
        if any(
            row.get(flag)
            for row in containers
            for flag in ("retracted", "superseded", "correction_pending", "extraction_candidate")
        ):
            limitations.append("resource_original_withdrawn_or_pending")
            continue
        rights = _rights(
            reference, version, permissions.get(dataset.registry_key, {}), synthetic, reference
        )
        if not rights.internal_analysis_allowed or not rights.excerpt_output_allowed:
            limitations.append("resource_use_not_permitted")
            continue
        facts = ResourceFacts.model_validate(
            (reference.metadata_json or {}).get("learning_resource", {})
        )
        if facts.url not in {source.url, version.artifact_url}:
            invalid("Resource URL differs from its persisted original source")
        earliest, _, precision = _date_interval(version.publication_date)
        if earliest and earliest > as_of.date():
            invalid("Resource publication is after the plan cutoff")
        item = EvidenceItem(
            id=f"learning_resource:{reference.id}",
            kind="learning_resource",
            record_id=reference.id,
            version_id=version.id,
            evidence_reference_id=reference.id,
            source_id=source.id,
            dataset_key=dataset.registry_key,
            evidence_class=str(source.evidence_class),
            scope="academic_benchmark",
            source_url=facts.url,
            publisher=source.publisher,
            title=source.title,
            locator=reference.locator,
            excerpt=reference.excerpt[:2000],
            publication_date=version.publication_date,
            date_precision=precision,
            retrieved_at=version.retrieved_at,
            review_status="reviewed",
            is_synthetic=synthetic,
            rights=rights,
            internal_eligible=True,
            model_eligible=rights.external_model_allowed,
            identity_reviewed=True,
            facts={
                "learning_resource": facts.model_dump(mode="json"),
                "skill_id": str(binding.skill_id),
                "related_skill_ids": [str(row) for row in facts.related_skill_ids],
                "prerequisite_skill_ids": [str(row) for row in facts.prerequisite_skill_ids],
                "duration_hours": str(facts.duration_hours)
                if facts.duration_hours is not None
                else None,
                "duration_component": facts.duration_component,
                "as_of": as_of.isoformat(),
                "content_sha256": version.content_sha256,
            },
        )
        resources.append(_resource(item))
        evidence.append(item)
    return resources, evidence, limitations


def validate_resources(resources, evidence, as_of=None):
    if as_of is not None and any(
        row.facts.get("as_of") != as_of.isoformat()
        for row in evidence
        if row.kind == "learning_resource"
    ):
        invalid("Resource verification changed the plan cutoff")
    expected = [_resource(item) for item in evidence if item.kind == "learning_resource"]
    if resources != expected:
        invalid("Learning resources differ from admitted original-source facts")


def duration_for(binding, evidence, as_of):
    if binding is None:
        return DurationEstimate()
    if not binding.reviewed or binding.reviewed_at > as_of:
        return DurationEstimate(basis="Duration basis not reviewed at the plan cutoff.")
    citations = []
    if binding.basis_type == "source":
        item = next((row for row in evidence if row.id == binding.reference_id), None)
        if item is None or not binding.quote or binding.quote not in item.excerpt:
            invalid("Duration requires an exact admitted original-source citation")
        actual = item.facts.get("duration_hours")
        if (
            actual is None
            or Decimal(str(actual)) != binding.hours
            or item.facts.get("duration_component", "learning") != binding.component
        ):
            invalid("Duration or effort component differs from original-source facts")
        citations = [CareerCitation(reference_id=item.id, quote=binding.quote)]
    return DurationEstimate(
        hours=binding.hours,
        component=binding.component,
        basis_type=binding.basis_type,
        basis=binding.basis,
        citations=citations,
        reviewed_at=binding.reviewed_at,
    )
