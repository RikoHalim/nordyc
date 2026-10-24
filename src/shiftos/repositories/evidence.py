"""Atomic immutable version loading, isolated from retrieval and parsing."""

import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from shiftos.models import Source
from shiftos.models.evidence import (
    AcademicStandard,
    AIImpactEvidence,
    Dataset,
    DatasetVersion,
    EvidenceReference,
    Occupation,
    OccupationalTask,
    OccupationSkill,
    SDGReference,
    Skill,
    WorkforceObservation,
)

MODELS = {
    "occupation": Occupation,
    "skill": Skill,
    "occupation_skill": OccupationSkill,
    "task": OccupationalTask,
    "workforce": WorkforceObservation,
    "ai_evidence": AIImpactEvidence,
    "academic_standard": AcademicStandard,
    "sdg": SDGReference,
}


class EvidenceLoadError(ValueError):
    def __init__(self, code, message, locator):
        super().__init__(message)
        self.code, self.message, self.locator = code, message, locator


def sync_registry(session, entries):
    for entry in entries:
        dataset = session.scalar(select(Dataset).where(Dataset.registry_key == entry.id))
        values = dict(
            name=entry.name,
            category=entry.category,
            registry_metadata=entry.model_dump(mode="json"),
        )
        if dataset is None:
            session.add(Dataset(registry_key=entry.id, **values))
        else:
            for key, value in values.items():
                setattr(dataset, key, value)
    session.flush()


def load_batch(
    session, dataset, entry, artifact, batch, *, parser_version, context, is_synthetic=False
):
    context_hash = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
    # Lock dataset to serialize competing imports without blocking unrelated datasets.
    session.scalar(select(Dataset).where(Dataset.id == dataset.id).with_for_update())
    existing = session.scalar(
        select(DatasetVersion).where(
            DatasetVersion.dataset_id == dataset.id,
            DatasetVersion.content_sha256 == artifact.sha256,
            DatasetVersion.parser_version == parser_version,
            DatasetVersion.context_sha256 == context_hash,
        )
    )
    if existing:
        return existing, False, existing.metadata_json.get("counts", {})
    source = Source(
        publisher=entry.publisher,
        title=entry.name[:255],
        url=entry.source_url,
        source_kind="external_dataset",
        evidence_class=("synthetic_demo" if is_synthetic else entry.evidence_class),
        is_synthetic=is_synthetic,
        license_status=entry.rights_status[:100],
        collected_at=artifact.retrieved_at,
        content_hash=artifact.sha256,
    )
    session.add(source)
    session.flush()
    version = DatasetVersion(
        dataset_id=dataset.id,
        source_id=source.id,
        content_sha256=artifact.sha256,
        parser_version=parser_version,
        context_sha256=context_hash,
        retrieved_at=artifact.retrieved_at,
        artifact_url=artifact.url,
        publication_date=entry.latest_verified_publication_date,
        is_synthetic=is_synthetic,
        metadata_json={
            "registry": entry.model_dump(mode="json"),
            "transform": context,
            "extraction": batch.metadata,
            "warnings": batch.warnings,
        },
    )
    session.add(version)
    session.flush()
    references, identities, counts, seen = {}, {}, Counter(), {}
    ordered = sorted(batch.records, key=lambda r: {"occupation": 0, "skill": 1}.get(r.kind, 2))
    for record in ordered:
        expected_class = {
            "occupation": "occupation_requirement",
            "skill": "occupation_requirement",
            "occupation_skill": "occupation_requirement",
            "task": "occupation_requirement",
            "workforce": "dated_workforce_signal",
            "ai_evidence": "dated_ai_capability",
            "academic_standard": "published_standard",
            "sdg": "published_standard",
        }.get(record.kind)
        # An AI-exposure contextual finding can originate in a workforce study.
        # Preserve that source class; it does not become measured AI capability.
        workforce_exposure_context = (
            record.kind == "ai_evidence"
            and record.data.get("impact_type") == "occupational_exposure"
            and entry.evidence_class == "dated_workforce_signal"
            and not record.data.get("capability")
        )
        if (
            not is_synthetic
            and expected_class
            and entry.evidence_class != expected_class
            and not workforce_exposure_context
        ):
            raise EvidenceLoadError(
                "evidence_class_mismatch",
                "Record kind does not match source evidence class.",
                record.locator,
            )
        identity = (record.kind, record.key)
        canonical = record.model_dump(mode="json")
        if identity in seen:
            if seen[identity] != canonical:
                raise ValueError("Conflicting duplicate record identity")
            continue
        seen[identity] = canonical
        reference = references.get(record.locator)
        if reference is None:
            reference = EvidenceReference(
                version_id=version.id,
                locator=record.locator,
                excerpt=record.excerpt,
                page_number=record.page_number,
                review_status=(
                    "reviewed" if record.review_status == "reviewed" else "needs_review"
                ),
                is_synthetic=is_synthetic,
            )
            session.add(reference)
            session.flush()
            references[record.locator] = reference
        elif reference.excerpt != record.excerpt:
            raise ValueError("Conflicting excerpts at one evidence locator")
        if record.kind == "pdf_candidate":
            reference.metadata_json = {"extraction_candidate": record.data}
            counts["pdf_candidate"] += 1
            continue
        model = MODELS[record.kind]
        data = dict(record.data)
        if record.kind == "workforce":
            for field in ("period_start", "period_end"):
                data[field] = date.fromisoformat(data[field])
            if data.get("value") is not None:
                data["value"] = Decimal(data["value"])
        if record.kind == "sdg" and data.get("description") is None:
            data["description"] = ""
        for field, kind in (
            ("occupation_external_id", "occupation"),
            ("skill_external_id", "skill"),
        ):
            external = data.pop(field, None)
            if external is not None:
                linked = identities.get((kind, external))
                if linked is None:
                    raise EvidenceLoadError(
                        "unmatched_classification",
                        "Unmatched classification; no guessed relationship imported",
                        record.locator,
                    )
                data[field.replace("external_", "")] = linked
        row = model(
            version_id=version.id,
            evidence_id=reference.id,
            external_id=record.key,
            is_synthetic=is_synthetic,
            **data,
        )
        session.add(row)
        session.flush()
        identities[identity] = row.id
        counts[record.kind] += 1
    version.metadata_json = {**version.metadata_json, "counts": dict(counts)}
    session.flush()
    return version, True, dict(counts)
