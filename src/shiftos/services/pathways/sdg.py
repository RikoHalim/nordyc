"""Explicit reviewed contributions to existing UN targets; never measured impact."""

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select

from shiftos.models import Dataset, DatasetVersion, EvidenceReference, SDGReference, Source
from shiftos.schemas.analysis import EvidenceItem
from shiftos.schemas.career import CareerCitation
from shiftos.schemas.pathways import SDGAlignment
from shiftos.services.analysis.orchestrator import _permissions
from shiftos.services.analysis.retrieval import _date_interval, _rights
from shiftos.services.pathways.resources import invalid, safe_url

TARGETS = {
    "assessed_competency_access": {"4.4"},
    "inclusive_learning_access": {"4.3", "4.5"},
    "research_innovation": {"9.5"},
    "resource_efficient_practice": {"12.2"},
}


@lru_cache(maxsize=1)
def _official():
    path = (
        Path(__file__).resolve().parents[4] / "data/reference_packs/un-sdg-resolution.reviewed.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        row["data"]["code"]: {
            **row["data"],
            "original_excerpt": row["excerpt"],
            "original_locator": row["locator"],
        }
        for row in payload["records"]
    }


def _align(snapshots, evidence, mappings, as_of):
    references = {row.id: row for row in evidence}
    sdgs = {str(row.record_id): row for row in evidence if row.kind == "sdg"}
    selected = {row.id: row for row in snapshots}
    found = {}
    for mapping in mappings:
        if mapping.recommendation_id not in selected:
            invalid("SDG relationship belongs to an unselected recommendation")
        if mapping.recommendation_id in found:
            invalid("Use one reviewed primary SDG relationship per recommendation")
        snapshot = selected[mapping.recommendation_id]
        item = sdgs.get(str(mapping.sdg_reference_id))
        if not mapping.reviewed or mapping.reviewed_at > as_of or item is None:
            found[snapshot.id] = SDGAlignment(
                recommendation_id=snapshot.id,
                status="insufficient_evidence",
                rationale="SDG contribution requires reviewed target and intervention evidence.",
            )
            continue
        facts = item.facts
        if facts["code"] not in TARGETS[mapping.mechanism]:
            invalid("The proposed mechanism does not establish a supported UN target relationship")
        if (
            snapshot.consideration_status != "eligible"
            or snapshot.recommendation.category in {"no_change", "request_review"}
            or snapshot.recommendation.evidence_sufficiency == "insufficient_evidence"
        ):
            found[snapshot.id] = SDGAlignment(
                recommendation_id=snapshot.id,
                status="insufficient_evidence",
                rationale="Unresolved or no-change proposals do not establish this contribution.",
            )
            continue
        allowed = {(row.reference_id, row.quote) for row in snapshot.recommendation.citations}
        for citation in mapping.citations:
            source = references.get(citation.reference_id)
            if (
                source is None
                or not citation.quote.strip()
                or citation.quote not in source.excerpt
                or (citation.reference_id, citation.quote) not in allowed
            ):
                invalid("SDG contribution requires exact supporting recommendation citations")
            skill = source.facts.get("skill_id")
            if skill is not None and str(snapshot.recommendation.skill_id) != str(skill):
                invalid("SDG relationship cites a different competency")
        found[snapshot.id] = SDGAlignment(
            recommendation_id=snapshot.id,
            status="possible_contribution",
            goal_code=facts["goal_code"],
            goal_title=facts["goal_title"],
            target_code=facts["code"],
            target_title=facts["title"],
            mechanism=mapping.mechanism,
            rationale=mapping.rationale,
            citations=[
                *mapping.citations,
                CareerCitation(reference_id=item.id, quote=item.excerpt),
            ],
            limitations=[
                "Reviewed proposed contribution; no measured or achieved SDG impact.",
                "UN target text is a normative benchmark, not evidence of university teaching.",
            ],
        )
    return [
        found.get(row.id)
        or SDGAlignment(
            recommendation_id=row.id,
            status="unmapped",
            rationale="No justified reviewed SDG contribution was supplied; no automatic goal tag.",
        )
        for row in snapshots
    ]


def admit_sdgs(
    session, mappings, recommendation_snapshots, evidence, settings, as_of, is_synthetic
):
    permissions, _ = _permissions(settings)
    admitted, limitations, seen = [], [], set()
    official = _official()
    for mapping in mappings:
        if not mapping.reviewed or mapping.reviewed_at > as_of or mapping.sdg_reference_id in seen:
            continue
        seen.add(mapping.sdg_reference_id)
        row = session.get(SDGReference, mapping.sdg_reference_id)
        version = session.get(DatasetVersion, row.version_id) if row else None
        reference = session.get(EvidenceReference, row.evidence_id) if row else None
        source = session.get(Source, version.source_id) if version else None
        dataset = session.get(Dataset, version.dataset_id) if version else None
        if (
            not all((row, version, reference, source, dataset))
            or reference.version_id != version.id
        ):
            invalid("SDG benchmark has incomplete source lineage")
        if any(
            value.is_synthetic != source.is_synthetic
            for value in (row, version, reference, dataset)
        ):
            invalid("SDG benchmark has inconsistent source labels")
        if row.is_synthetic and not is_synthetic:
            invalid("Synthetic SDG evidence cannot support a real programme")
        canonical = official.get(row.code)
        if (
            not canonical
            or row.kind != "target"
            or any(
                getattr(row, key) != canonical[key]
                for key in ("kind", "goal_code", "title", "description")
            )
        ):
            invalid("SDG identifier or text differs from the reviewed official UN benchmark")
        if (
            " ".join(reference.excerpt.split()) != " ".join(canonical["original_excerpt"].split())
            or reference.locator != canonical["original_locator"]
        ):
            invalid("SDG citation differs from the admitted original UN passage")
        goal = session.scalar(
            select(SDGReference).where(
                SDGReference.version_id == version.id, SDGReference.code == row.goal_code
            )
        )
        if not goal or goal.title != official[row.goal_code]["title"] or goal.kind != "goal":
            invalid("SDG target has no exact official parent goal")
        if not row.is_synthetic and (
            dataset.registry_key != "F-UN-SDG-RES70-1"
            or str(source.evidence_class) != "published_standard"
            or (row.metadata_json or {}).get("document_symbol") != "A/RES/70/1"
            or not safe_url(source.url)
            or source.url
            not in {
                canonical["metadata_json"]["source_url"],
                canonical["metadata_json"]["source_url"].split("/files/", 1)[0],
            }
            or version.artifact_url != canonical["metadata_json"]["source_url"]
            or source.publisher != "United Nations General Assembly"
        ):
            invalid("SDG benchmark is not the admitted attributed UN original")
        if (
            reference.review_status != "reviewed"
            or version.retrieved_at > as_of
            or (source.collected_at and source.collected_at > as_of)
            or (source.published_at and source.published_at > as_of)
        ):
            limitations.append("sdg_original_not_reviewed_at_cutoff")
            continue
        if any(
            container.get(flag)
            for container in (
                row.metadata_json or {},
                reference.metadata_json or {},
                version.metadata_json or {},
            )
            for flag in ("retracted", "superseded", "correction_pending", "extraction_candidate")
        ):
            limitations.append("sdg_original_withdrawn_or_pending")
            continue
        rights = _rights(
            row, version, permissions.get(dataset.registry_key, {}), row.is_synthetic, reference
        )
        if not rights.internal_analysis_allowed or not rights.excerpt_output_allowed:
            limitations.append("sdg_benchmark_use_not_permitted")
            continue
        goal_reference = session.get(EvidenceReference, goal.evidence_id)
        goal_canonical = official[row.goal_code]
        if (
            goal.is_synthetic != row.is_synthetic
            or goal_reference is None
            or goal_reference.version_id != version.id
            or goal_reference.is_synthetic != row.is_synthetic
            or " ".join(goal_reference.excerpt.split())
            != " ".join(goal_canonical["original_excerpt"].split())
            or goal_reference.locator != goal_canonical["original_locator"]
        ):
            invalid("SDG parent goal differs from its original UN passage")
        goal_rights = _rights(
            goal,
            version,
            permissions.get(dataset.registry_key, {}),
            goal.is_synthetic,
            goal_reference,
        )
        if (
            goal_reference.review_status != "reviewed"
            or not goal_rights.internal_analysis_allowed
            or not goal_rights.excerpt_output_allowed
            or any(
                container.get(flag)
                for container in (goal.metadata_json or {}, goal_reference.metadata_json or {})
                for flag in (
                    "retracted",
                    "superseded",
                    "correction_pending",
                    "extraction_candidate",
                )
            )
        ):
            limitations.append("sdg_parent_goal_not_admissible")
            continue
        earliest, _, precision = _date_interval(version.publication_date)
        if earliest and earliest > as_of.date():
            invalid("SDG benchmark publication is after the cutoff")
        admitted.append(
            EvidenceItem(
                id=f"sdg:{row.id}",
                kind="sdg",
                record_id=row.id,
                version_id=version.id,
                evidence_reference_id=reference.id,
                source_id=source.id,
                dataset_key=dataset.registry_key,
                evidence_class=str(source.evidence_class),
                scope="academic_benchmark",
                source_url=source.url,
                publisher=source.publisher,
                title=source.title,
                locator=reference.locator,
                excerpt=reference.excerpt[:2000],
                publication_date=version.publication_date,
                date_precision=precision,
                retrieved_at=version.retrieved_at,
                review_status="reviewed",
                is_synthetic=row.is_synthetic,
                rights=rights,
                internal_eligible=True,
                model_eligible=rights.external_model_allowed,
                identity_reviewed=True,
                facts={
                    "code": row.code,
                    "goal_code": row.goal_code,
                    "title": row.title,
                    "goal_title": goal.title,
                    "description": row.description,
                    "document_symbol": "A/RES/70/1",
                    "content_sha256": version.content_sha256,
                    "original_artifact_url": version.artifact_url,
                },
                limitations=[
                    "Normative UN benchmark; contribution is an explicitly reviewed inference."
                ],
            )
        )
        if not any(item.record_id == goal.id for item in admitted):
            target_item = admitted[-1]
            admitted.append(
                target_item.model_copy(
                    update={
                        "id": f"sdg:{goal.id}",
                        "record_id": goal.id,
                        "evidence_reference_id": goal_reference.id,
                        "locator": goal_reference.locator,
                        "excerpt": goal_reference.excerpt[:2000],
                        "rights": goal_rights,
                        "model_eligible": goal_rights.external_model_allowed,
                        "facts": {
                            **target_item.facts,
                            "code": goal.code,
                            "title": goal.title,
                            "description": goal.description,
                        },
                    }
                )
            )
    return (
        _align(recommendation_snapshots, [*evidence, *admitted], mappings, as_of),
        admitted,
        limitations,
    )


def validate_sdg_alignments(alignments, snapshots, evidence, mappings, as_of):
    for item in evidence:
        if item.kind == "sdg":
            facts = item.facts
            canonical = _official().get(facts.get("code"))
            if (
                not canonical
                or any(
                    facts.get(key) != canonical[key]
                    for key in ("code", "title", "goal_code", "description")
                )
                or facts.get("goal_title") != _official()[canonical["goal_code"]]["title"]
            ):
                invalid("SDG facts differ from the official UN target")
            if (
                " ".join(item.excerpt.split()) != " ".join(canonical["original_excerpt"].split())
                or item.locator != canonical["original_locator"]
                or (
                    not item.is_synthetic
                    and (
                        item.source_url
                        not in {
                            canonical["metadata_json"]["source_url"],
                            canonical["metadata_json"]["source_url"].split("/files/", 1)[0],
                        }
                        or facts.get("original_artifact_url")
                        != canonical["metadata_json"]["source_url"]
                        or item.publisher != "United Nations General Assembly"
                    )
                )
            ):
                invalid("SDG citation or attribution differs from the official UN original")
    if alignments != _align(snapshots, evidence, mappings, as_of):
        invalid("SDG contributions differ from the reviewed evidence relationships")
