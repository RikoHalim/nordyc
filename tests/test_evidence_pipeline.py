"""Entirely synthetic offline ETL fixtures; never evidence of actual labour demand."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from shiftos.models.evidence import DatasetVersion, EvidenceIngestionJob, WorkforceObservation
from shiftos.services.evidence.acquisition import DatasetFetcher
from shiftos.services.evidence.pipeline import run_ingestion
from shiftos.services.ingestion.fetcher import FetchError

REGISTRY = Path(__file__).resolve().parents[1] / "data/dataset_registry.csv"


@pytest.fixture
def synthetic_etl(tmp_path):
    data = tmp_path / "synthetic.csv"
    data.write_text(
        "date,sector,sex,proportion\n2024-01-01,synthetic_sector,both,12.5\n"
        "2025-01-01,synthetic_sector,both,13.0\n",
        encoding="utf-8",
    )
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "D-EMPLOYMENT-SECTOR": {
                    "adapter": "employment_sector",
                    "format": "csv",
                    "reuse_reviewed": True,
                    "instructions": "Synthetic fixture only; no real workforce evidence.",
                }
            }
        ),
        encoding="utf-8",
    )
    return dict(
        registry_path=REGISTRY,
        policy_path=policy,
        dataset_ids=["D-EMPLOYMENT-SECTOR"],
        local_path=data,
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        is_synthetic=True,
    )


def test_persist_repeat_and_changed_version(database, synthetic_etl):
    first = run_ingestion(database, **synthetic_etl)[0]
    assert first["status"] == "SUCCEEDED", first
    assert first["records_imported"] == 2
    second = run_ingestion(database, **synthetic_etl)[0]
    assert second["status"] == "UNCHANGED"
    assert second["records_imported"] == 0
    path = synthetic_etl["local_path"]
    path.write_text(path.read_text().replace("13.0", "14.0"))
    third = run_ingestion(database, **synthetic_etl)[0]
    assert third["status"] == "SUCCEEDED"
    assert third["version_id"] != first["version_id"]
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DatasetVersion)) == 2
        assert session.scalar(select(func.count()).select_from(WorkforceObservation)) == 4
        assert all(row.is_synthetic for row in session.scalars(select(WorkforceObservation)))


def test_corrupt_import_is_atomic_with_durable_failure(database, synthetic_etl):
    synthetic_etl["local_path"].write_bytes(b"<html>Login required</html>")
    report = run_ingestion(database, **synthetic_etl)[0]
    assert report["status"] == "FAILED"
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DatasetVersion)) == 0
        assert session.scalar(select(EvidenceIngestionJob)).error == "import_rejected"


def test_registry_reports_manual_and_skipped(database):
    reports = run_ingestion(database, dataset_ids=["F-UN-SDG", "A-XMUM-01"])
    assert {r["status"] for r in reports} == {"MANUAL_REQUIRED", "SKIPPED"}
    assert all(r["records_imported"] == 0 for r in reports)


def dataset_fetcher(handler, **kwargs):
    return DatasetFetcher(
        {"storage.dosm.gov.my"},
        enabled=True,
        terms_reviewed=True,
        transport=httpx.MockTransport(handler),
        resolver=lambda _: ["8.8.8.8"],
        sleep=lambda _: None,
        **kwargs,
    )


def test_mocked_download_checks_robots_and_integrity():
    seen = []

    def handler(request):
        seen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(
            200, content=b"date,value\n2025,1\n", headers={"content-type": "text/csv"}
        )

    with dataset_fetcher(handler) as fetcher:
        artifact = fetcher.fetch("https://storage.dosm.gov.my/synthetic.csv")
    assert seen == ["/robots.txt", "/synthetic.csv"]
    assert len(artifact.sha256) == 64


@pytest.mark.parametrize("case", ["restricted", "robots", "landing", "corrupt_mime", "oversize"])
def test_download_failures(case):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\n" + ("Disallow: /" if case == "robots" else "Allow: /")
            )
        if case == "restricted":
            return httpx.Response(403)
        content = b"<html>CAPTCHA</html>" if case == "landing" else b"x" * 101
        return httpx.Response(
            200,
            content=content,
            headers={"content-type": "text/html" if case == "corrupt_mime" else "text/csv"},
        )

    with dataset_fetcher(handler, max_bytes=100 if case == "oversize" else 1000) as fetcher:
        with pytest.raises(FetchError):
            fetcher.fetch("https://storage.dosm.gov.my/synthetic.csv")


def test_private_network_is_rejected():
    with DatasetFetcher(
        {"storage.dosm.gov.my"}, enabled=True, terms_reviewed=True, resolver=lambda _: ["127.0.0.1"]
    ) as fetcher:
        with pytest.raises(FetchError, match="not permitted"):
            fetcher.fetch("https://storage.dosm.gov.my/synthetic.csv")


def test_no_download_when_disabled():
    with DatasetFetcher({"storage.dosm.gov.my"}) as fetcher:
        with pytest.raises(FetchError, match="review"):
            fetcher.fetch("https://storage.dosm.gov.my/synthetic.csv")


def test_failed_commit_never_reports_success(database, synthetic_etl, monkeypatch):
    from sqlalchemy.orm import Session

    original_commit = Session.commit
    commits = 0

    def fail_data_commit(session):
        nonlocal commits
        commits += 1
        if commits == 3:
            raise RuntimeError("Synthetic simulated database failure")
        return original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_data_commit)
    report = run_ingestion(database, **synthetic_etl)[0]
    assert report["status"] == "FAILED"
    assert report["records_imported"] == 0
    assert "version_id" not in report
    with database.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DatasetVersion)) == 0


def test_checked_in_offline_pack_is_explicitly_synthetic_and_repeatable(database):
    root = REGISTRY.parents[1]
    options = dict(
        registry_path=root / "fixtures/evidence/dataset_registry.synthetic.csv",
        policy_path=root / "fixtures/evidence/policy.synthetic.json",
        dataset_ids=["SYNTHETIC-EVIDENCE"],
        local_path=root / "fixtures/evidence/records.synthetic.json",
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        is_synthetic=True,
    )
    result = run_ingestion(database, **options)[0]
    assert result["status"] == "SUCCEEDED", result
    assert result["records_imported"] == 21
    assert result["counts"]["occupation_skill"] == 3
    assert result["counts"]["sdg"] == 1
    assert run_ingestion(database, **options)[0]["status"] == "UNCHANGED"
