"""All inserted records here are explicitly invented offline test fixtures."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shiftos.models import (
    AcademicStandard,
    AIImpactEvidence,
    Dataset,
    DatasetVersion,
    EvidenceIngestionJob,
    EvidenceProcessingLog,
    EvidenceReference,
    Occupation,
    OccupationalTask,
    OccupationSkill,
    SDGReference,
    Skill,
    Source,
    WorkforceObservation,
)


@pytest.fixture
def evidence_records(session: Session) -> dict:
    source = Source(
        publisher="Synthetic Evidence Test Publisher",
        title="Synthetic multi-discipline pack",
        url="https://example.invalid/synthetic-evidence",
        evidence_class="synthetic_demo",
        is_synthetic=True,
    )
    dataset = Dataset(
        registry_key="SYNTHETIC-TEST",
        name="Synthetic test data",
        category="synthetic_demo",
        registry_metadata={"warning": "invented test records"},
        is_synthetic=True,
    )
    session.add_all([source, dataset])
    session.flush()
    versions = []
    references = []
    for index in range(2):
        version = DatasetVersion(
            dataset_id=dataset.id,
            source_id=source.id,
            content_sha256=str(index) * 64,
            parser_version="synthetic-v1",
            retrieved_at=datetime(2026, 10, 20 + index, tzinfo=UTC),
            publication_date="2026" if index == 0 else None,
            artifact_url=source.url,
            is_synthetic=True,
        )
        session.add(version)
        session.flush()
        reference = EvidenceReference(
            version_id=version.id,
            locator=f"synthetic:table:{index}",
            excerpt="Synthetic reference statement",
            page_number=index + 1,
            review_status="needs_review",
            is_synthetic=True,
        )
        session.add(reference)
        session.flush()
        session.add(
            WorkforceObservation(
                version_id=version.id,
                evidence_id=reference.id,
                external_id="synthetic-workforce",
                occupation_label="Synthetic professionals",
                classification_system="synthetic",
                classification_code="SYNTHETIC-2",
                sector="Synthetic cross-sector",
                period_start=date(2026, 1 + 3 * index, 1),
                period_end=date(2026, 3 + 3 * index, 30),
                indicator="synthetic_advertisements",
                value=Decimal(100 + index),
                unit="count",
                limitations="Invented counts; occupation totals do not measure individual skills",
                is_synthetic=True,
            )
        )
        versions.append(version)
        references.append(reference)
    base = {"version_id": versions[0].id, "evidence_id": references[0].id, "is_synthetic": True}
    occupation = Occupation(
        **base,
        external_id="synthetic:accountant",
        taxonomy="synthetic",
        label="Synthetic accountant",
    )
    skill = Skill(
        **base, external_id="synthetic:skill", taxonomy="synthetic", label="Synthetic reporting"
    )
    session.add_all([occupation, skill])
    session.flush()
    session.add_all(
        [
            Occupation(
                **base,
                external_id="synthetic:biologist",
                taxonomy="synthetic",
                label="Synthetic biologist",
            ),
            OccupationSkill(
                **base,
                external_id="synthetic:relation",
                occupation_id=occupation.id,
                skill_id=skill.id,
                relationship="essential",
            ),
            OccupationalTask(
                **base,
                external_id="synthetic:task",
                occupation_id=occupation.id,
                description="Synthetic reporting task",
            ),
            AIImpactEvidence(
                **base,
                external_id="synthetic:ai",
                occupation_label=occupation.label,
                statement="Synthetic exposure statement",
                impact_type="occupational_exposure",
                limitations="Invented test evidence; exposure is not replacement probability",
            ),
            AcademicStandard(
                **base,
                external_id="synthetic:standard",
                discipline="Synthetic accounting",
                title="Synthetic benchmark",
                statement="Synthetic competency expectation",
            ),
            SDGReference(
                **base,
                external_id="synthetic:goal",
                code="8",
                kind="goal",
                goal_code="8",
                title="Synthetic SDG fixture",
                description="Synthetic description",
            ),
        ]
    )
    job = EvidenceIngestionJob(
        dataset_id=dataset.id,
        version_id=versions[0].id,
        status="SUCCEEDED",
        records_imported=9,
        started_at=datetime(2026, 10, 20, tzinfo=UTC),
        completed_at=datetime(2026, 10, 20, tzinfo=UTC),
        is_synthetic=True,
        result_json={"warning": "synthetic fixture"},
    )
    session.add(job)
    session.flush()
    session.add(
        EvidenceProcessingLog(
            job_id=job.id,
            level="warning",
            code="synthetic_fixture",
            message="Invented test data",
            locator="synthetic:manifest",
            is_synthetic=True,
        )
    )
    session.commit()
    return {
        "dataset": dataset,
        "source": source,
        "versions": versions,
        "references": references,
        "occupation": occupation,
        "skill": skill,
        "job": job,
    }


def test_dataset_versions_status_and_precise_provenance(client: TestClient, evidence_records: dict):
    records = evidence_records
    response = client.get("/api/v1/evidence/datasets?category=synthetic_demo&limit=1")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["latest_ingestion_status"] == "SUCCEEDED"
    assert response.json()["items"][0]["registry_metadata"]["warning"] == "invented test records"
    path = f"/api/v1/evidence/datasets/{records['dataset'].id}"
    assert client.get(path).json()["is_synthetic"] is True
    assert client.get(path + "/versions").json()["total"] == 2
    assert client.get(path + "/jobs").json()["items"][0]["status"] == "SUCCEEDED"
    version = records["versions"][0]
    data = client.get(f"/api/v1/evidence/versions/{version.id}/provenance").json()
    assert data["source"]["id"] == str(records["source"].id)
    assert data["source"]["evidence_class"] == "synthetic_demo"
    assert data["version"]["publication_date"] == "2026"
    assert data["version"]["retrieved_at"].startswith("2026-10-20")
    assert data["record_counts"]["occupations"] == 2
    second = client.get(f"/api/v1/evidence/versions/{records['versions'][1].id}").json()
    assert second["publication_date"] is None
    reference = records["references"][0]
    data = client.get(f"/api/v1/evidence/references/{reference.id}/provenance").json()
    assert data["evidence"]["page_number"] == 1
    assert data["evidence"]["review_status"] == "needs_review"
    assert client.get("/api/v1/evidence/datasets?is_synthetic=false").json()["total"] == 0


def test_multi_discipline_occupation_skills_tasks_and_safe_search(
    client: TestClient,
    evidence_records: dict,
):
    occupation = evidence_records["occupation"]
    path = "/api/v1/evidence/occupations"
    assert client.get(path).json()["total"] == 2
    assert client.get(path + "?q=biologist").json()["total"] == 1
    assert client.get(path + "?q=%25").json()["total"] == 0
    assert client.get(path + "?taxonomy=unknown").json()["total"] == 0
    assert client.get(f"{path}/{occupation.id}").json()["label"] == "Synthetic accountant"
    data = client.get(f"{path}/{occupation.id}/skills").json()
    assert data["items"][0]["relationship"] == "essential"
    assert data["items"][0]["skill"]["label"] == "Synthetic reporting"
    assert data["items"][0]["evidence_id"] == str(evidence_records["references"][0].id)
    assert client.get(f"{path}/{occupation.id}/tasks").json()["total"] == 1
    assert client.get("/api/v1/evidence/skills?q=reporting").json()["total"] == 1


def test_workforce_historical_snapshots_and_filters(client: TestClient, evidence_records: dict):
    path = "/api/v1/evidence/workforce-observations"
    response = client.get(
        path + "?indicator=synthetic_advertisements&classification_code=SYNTHETIC-2"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert [row["period_start"] for row in data["items"]] == ["2026-01-01", "2026-04-01"]
    assert [Decimal(row["value"]) for row in data["items"]] == [100, 101]
    assert all(row["occupation_id"] is None for row in data["items"])
    assert all("skill_id" not in row for row in data["items"])
    assert client.get(path + "?period_start=2026-04-01&period_end=2026-06-30").json()["total"] == 1
    dataset = evidence_records["dataset"].id
    version = evidence_records["versions"][0].id
    assert client.get(path + f"?dataset_id={dataset}&version_id={version}").json()["total"] == 1
    assert client.get(path + "?geography=US").json()["total"] == 0


@pytest.mark.parametrize(
    "path,query,expected",
    [
        ("ai-impact", "impact_type=occupational_exposure", 1),
        ("ai-impact", "impact_type=future_prediction", 0),
        ("academic-standards", "discipline=Synthetic%20accounting", 1),
        ("academic-standards", "discipline=unknown", 0),
        ("sdg-references", "kind=goal&goal_code=8", 1),
        ("sdg-references", "kind=target", 0),
        ("references", "review_status=needs_review", 2),
    ],
)
def test_reference_family_filters(client, evidence_records, path, query, expected):
    response = client.get(f"/api/v1/evidence/{path}?{query}")
    assert response.status_code == 200
    assert response.json()["total"] == expected


def test_jobs_and_logs_are_visible(client: TestClient, evidence_records: dict):
    job = evidence_records["job"]
    path = "/api/v1/evidence/ingestion-jobs"
    assert client.get(path + "?status=FAILED").json()["total"] == 0
    assert client.get(path + f"?dataset_id={job.dataset_id}").json()["total"] == 1
    assert client.get(path + f"/{job.id}").json()["records_imported"] == 9
    data = client.get(path + f"/{job.id}/logs").json()
    assert data["items"][0]["code"] == "synthetic_fixture"


@pytest.mark.parametrize(
    "path",
    [
        "datasets",
        "versions",
        "references",
        "occupations",
        "ingestion-jobs",
    ],
)
def test_evidence_missing_resources_have_documented_errors(client: TestClient, path: str):
    response = client.get(f"/api/v1/evidence/{path}/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_evidence_read_api_validation_and_no_ingestion_endpoint(client: TestClient):
    assert client.get("/api/v1/evidence/datasets?limit=101").status_code == 422
    assert client.get("/api/v1/evidence/datasets?offset=-1").status_code == 422
    assert client.get("/api/v1/evidence/versions/invalid").status_code == 422
    assert client.get("/api/v1/evidence/workforce-observations?period_start=bad").status_code == 422
    assert client.post("/api/v1/evidence/datasets", json={}).status_code == 405
    paths = client.get("/openapi.json").json()["paths"]
    assert all(set(methods) <= {"get"} for path, methods in paths.items() if "/evidence/" in path)


def test_version_identity_and_cross_version_evidence_are_enforced(
    session: Session,
    evidence_records: dict,
):
    first, second = evidence_records["versions"]
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            DatasetVersion(
                dataset_id=first.dataset_id,
                source_id=first.source_id,
                content_sha256=first.content_sha256,
                parser_version=first.parser_version,
                retrieved_at=first.retrieved_at,
                artifact_url=first.artifact_url,
                is_synthetic=True,
            )
        )
        session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            Skill(
                version_id=second.id,
                evidence_id=evidence_records["references"][0].id,
                external_id="synthetic:wrong-version",
                taxonomy="synthetic",
                label="Synthetic invalid",
                is_synthetic=True,
            )
        )
        session.flush()
    assert len(session.scalars(select(DatasetVersion)).all()) == 2


def test_cross_snapshot_occupation_relationship_is_rejected(session, evidence_records):
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            OccupationalTask(
                version_id=evidence_records["versions"][1].id,
                evidence_id=evidence_records["references"][1].id,
                external_id="synthetic:wrong-occupation-version",
                occupation_id=evidence_records["occupation"].id,
                description="Synthetic invalid cross-version task",
                is_synthetic=True,
            )
        )
        session.flush()
