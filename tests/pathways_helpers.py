"""Labelled Phase 6 fixtures use real offline jobs, explicit reviews and source ETL."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, UUID, uuid5

from career_helpers import TOKEN, career_settings, seed_career
from fastapi.testclient import TestClient
from sqlalchemy import select

from shiftos.core.enums import EvidenceClass
from shiftos.main import create_app
from shiftos.models import (
    AIImpactEvidence,
    CareerRecommendation,
    CareerRun,
    Dataset,
    DatasetVersion,
    EvidenceReference,
    SDGReference,
    Source,
)
from shiftos.repositories.career import append_review
from shiftos.schemas.career import CareerCitation, ReviewRequest
from shiftos.schemas.pathways import PlanRequest
from shiftos.services.evidence.pipeline import run_ingestion
from shiftos.services.ingestion.worker import run_once

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/academic_pathways.synthetic.json"


def seed_parent(session, database, *, approve=True, observed_ai=False):
    """The test operator's explicit fictional decisions are never engine auto-approval."""
    records = seed_career(session)
    if observed_ai:
        quote = (
            "Explicit fictional observation: a synthetic professional data-modelling task "
            "used a scripted AI tool to suggest schema checks; reviewers still validated "
            "the result. This is a synthetic bounded capability observation, not Malaysian "
            "adoption, labour demand or replacement evidence."
        )
        reference = EvidenceReference(
            version_id=records.version.id,
            locator="synthetic:observed-ai-task",
            excerpt=quote,
            review_status="reviewed",
            is_synthetic=True,
        )
        session.add(reference)
        session.flush()
        session.add(
            AIImpactEvidence(
                version_id=records.version.id,
                evidence_id=reference.id,
                external_id="synthetic-observed-modelling-task",
                occupation_id=records.occupations["analyst"].id,
                statement=quote,
                task="Review the fictional relational model",
                capability="Suggest bounded schema checks",
                impact_type="observed_capability",
                study_period="Explicit synthetic fixture study period",
                limitations="Synthetic task; local adoption and displacement remain unknown.",
                metadata_json={
                    "model": "Synthetic scripted tool",
                    "related_disciplines": ["computing"],
                },
                is_synthetic=True,
            )
        )
        session.commit()
    settings = career_settings()
    with TestClient(create_app(settings=settings, database=database)) as client:
        client.headers["X-Analysis-Token"] = TOKEN
        queued = client.post(
            f"/api/v1/programmes/{records.programme.id}/career-analyses",
            json=records.request.model_dump(mode="json"),
        )
        assert queued.status_code == 202, queued.text
        assert run_once(database, settings) == UUID(queued.json()["job_id"])
        parent = client.get(f"/api/v1/career-analyses/{queued.json()['id']}")
        assert parent.status_code == 200, parent.text
        assert parent.json()["status"] == "PARTIAL"
        run_id = UUID(queued.json()["id"])
    session.expire_all()
    run = session.get(CareerRun, run_id)
    recommendations = session.scalars(
        select(CareerRecommendation)
        .where(CareerRecommendation.run_id == run_id)
        .order_by(CareerRecommendation.recommendation_key)
    ).all()
    reviews = []
    if approve:
        for row in recommendations:
            category = row.result_json["category"]
            decision = (
                "no_change_required"
                if category == "no_change"
                else "under_review"
                if category == "request_review"
                else "approved"
            )
            reviews.append(
                append_review(
                    session,
                    row.id,
                    ReviewRequest(
                        decision=decision,
                        reason=(
                            "Explicit fictional authenticated test-operator decision for pathway "
                            "consideration only; no real academic approval or curriculum change."
                        ),
                        expected_recommendation_version=row.version_sha256,
                    ),
                    settings,
                )
            )
    by_skill = {
        key: next(
            row for row in recommendations if row.result_json.get("skill_id") == str(skill.id)
        )
        for key, skill in records.skills.items()
    }
    return SimpleNamespace(
        records=records,
        career_fixture=records,
        settings=settings,
        parent=run,
        parent_run=run,
        recommendations=recommendations,
        by_skill=by_skill,
        reviews=reviews,
        data=json.loads(FIXTURE.read_text(encoding="utf-8")),
    )


def import_official_sdgs(database):
    """Reuse stored original provenance; no fresh UN download or made-up target text."""
    path = ROOT / "data/reference_packs/un-sdg-resolution.reviewed.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = run_ingestion(
        database,
        registry_path=ROOT / "data/dataset_registry.csv",
        policy_path=ROOT / "data/evidence_acquisition.json",
        dataset_ids=["F-UN-SDG-RES70-1"],
        local_path=path,
        retrieved_at=datetime.fromisoformat(payload["metadata"]["original_retrieved_at"]),
        is_synthetic=False,
    )[0]
    assert report["status"] in {"SUCCEEDED", "UNCHANGED"}, report
    assert report["records_imported"] in {0, 186}
    with database.session_factory() as session:
        targets = {row.code: row for row in session.scalars(select(SDGReference))}
        assert targets["4.4"].kind == "target" and targets["4"].kind == "goal"
        assert not targets["4.4"].is_synthetic
    return targets, report


def seed_pathways(
    session, database, tmp_path=None, *, approve=True, include_sdgs=True, observed_ai=False
):
    """Fictional resources plus authentic UN benchmark text; no live verification claim."""
    fixture = seed_parent(session, database, approve=approve, observed_ai=observed_ai)
    now = datetime.now(UTC)
    collected = now - timedelta(minutes=1)
    resource_rows, resource_sources, resource_versions = {}, {}, {}
    rights = {
        "internal_analysis_allowed": True,
        "external_model_allowed": True,
        "excerpt_output_allowed": True,
        "basis": "Explicit synthetic original-resource fixture permission only.",
    }
    bindings = []
    for item in fixture.data["resources"]:

        def identity(kind, resource_key=item["key"]):
            return uuid5(NAMESPACE_URL, f"{fixture.data['fixture_id']}:{resource_key}:{kind}")

        source = Source(
            id=identity("source"),
            publisher=item["publisher"],
            title=item["title"],
            url=item["url"],
            evidence_class=EvidenceClass.SYNTHETIC_DEMO,
            is_synthetic=True,
            collected_at=collected,
            license_status="Synthetic fixture only, not actual provider availability",
        )
        dataset = Dataset(
            id=identity("dataset"),
            registry_key=f"SYNTHETIC-RESOURCE-{item['key'].upper()}",
            name=item["title"],
            category="learning_resource",
            is_synthetic=True,
        )
        session.add_all([source, dataset])
        session.flush()
        version = DatasetVersion(
            id=identity("version"),
            dataset_id=dataset.id,
            source_id=source.id,
            content_sha256=hashlib.sha256(item["quote"].encode()).hexdigest(),
            parser_version="synthetic-reviewed-original-1",
            retrieved_at=collected,
            publication_date=(now - timedelta(days=1)).date().isoformat(),
            artifact_url=item["url"],
            is_synthetic=True,
            metadata_json={"edition": "synthetic-1", "analysis_permissions": rights},
        )
        session.add(version)
        session.flush()
        resource_metadata = {
            "name": item["title"],
            "resource_type": item["resource_type"],
            "url": item["url"],
            "related_skill_ids": [str(fixture.records.skills[item["skill"]].id)],
            "prerequisite_skill_ids": [
                str(fixture.records.skills[key].id)
                for key in item.get("prerequisite_skill_keys", [])
            ],
            "access_status": "unknown",
            "cost_status": "unknown",
            "cost_amount": None,
            "cost_currency": None,
            "verified_at": collected.isoformat(),
            "licence_limitations": item["label"],
        }
        if item["learning_hours"] is not None:
            resource_metadata.update(
                duration_hours=item["learning_hours"], duration_component="learning"
            )
        reference = EvidenceReference(
            id=identity("reference"),
            version_id=version.id,
            locator=f"synthetic:{item['key']}:original",
            excerpt=item["quote"],
            review_status="reviewed",
            is_synthetic=True,
            metadata_json={"learning_resource": resource_metadata, "analysis_permissions": rights},
        )
        session.add(reference)
        session.flush()
        (
            resource_rows[item["key"]],
            resource_sources[item["key"]],
            resource_versions[item["key"]],
        ) = reference, source, version
        bindings.append(
            {
                "reference_id": reference.id,
                "skill_id": fixture.records.skills[item["skill"]].id,
                "reviewed": True,
                "reviewed_at": now,
                "basis": "Explicit fictional resource-to-competency review; not live verification.",
            }
        )
    session.commit()
    targets, sdg_report = import_official_sdgs(database) if include_sdgs else ({}, None)
    sdg_mappings = []
    parent_evidence = {row["id"]: row for row in fixture.parent.result_json["evidence"]}
    if include_sdgs:
        for skill in ("model", "security"):
            recommendation = fixture.by_skill[skill]
            citations = [
                citation
                for citation in recommendation.result_json["citations"]
                if parent_evidence[citation["reference_id"]]["facts"].get("skill_id")
                == str(fixture.records.skills[skill].id)
            ]
            assert citations
            sdg_mappings.append(
                {
                    "recommendation_id": recommendation.id,
                    "sdg_reference_id": targets["4.4"].id,
                    "mechanism": "assessed_competency_access",
                    "rationale": fixture.data["sdg_reference"]["relationship"],
                    "citations": [citations[-1]],
                    "reviewed": True,
                    "reviewed_at": now,
                }
            )
    request = PlanRequest(
        mode="offline",
        recommendation_ids=[row.id for row in fixture.recommendations],
        resources=bindings,
        durations=[
            {
                "recommendation_id": fixture.by_skill["model"].id,
                "step_key": "practice",
                "hours": 3,
                "component": "learning",
                "basis_type": "source",
                "reference_id": f"learning_resource:{resource_rows['model-workbook'].id}",
                "quote": resource_rows["model-workbook"].excerpt,
                "basis": "Synthetic provider effort; excludes assessment and calendar time.",
                "reviewed": True,
                "reviewed_at": now,
            }
        ],
        scenarios=[
            {
                "key": "gradual_workforce_transformation",
                "assumption": "prioritise_incremental_coverage",
                "rationale": fixture.data["scenarios"][0]["assumption"],
            },
            {
                "key": "accelerated_ai_adoption",
                "assumption": "prioritise_assessment_review",
                "rationale": fixture.data["scenarios"][1]["assumption"],
            },
        ],
        sdg_mappings=sdg_mappings,
    )
    fixture.request, fixture.now = request, datetime.now(UTC)
    if observed_ai:
        task = next(
            row for row in fixture.parent.result_json["evidence"] if row["kind"] == "ai_evidence"
        )
        accelerated = next(row for row in request.scenarios if row.key == "accelerated_ai_adoption")
        accelerated.supporting_citations = [
            CareerCitation(reference_id=task["id"], quote=task["excerpt"])
        ]
    fixture.resources, fixture.resource_sources, fixture.resource_versions = (
        resource_rows,
        resource_sources,
        resource_versions,
    )
    fixture.sdg_targets, fixture.sdg_report = targets, sdg_report
    return fixture
