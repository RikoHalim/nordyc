"""Acceptance guard checks; no real Brave, source-acquisition or model requests."""

import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from test_analysis_research import research_setup, runner  # noqa: F401 - imported fixture

from shiftos.core.config import Settings
from shiftos.models import DatasetVersion, EvidenceReference, WorkforceObservation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def driver(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import verify_phase43

    monkeypatch.setattr(verify_phase43, "CASE", tmp_path)
    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda *a, **k: pytest.fail("No external requests allowed"),
    )
    return verify_phase43


def test_missing_key_preflight_is_nonbillable_and_preserves_gates(driver, monkeypatch):
    monkeypatch.setattr(
        driver,
        "configuration",
        lambda: Settings(
            _env_file=None,
            brave_search_api_key=None,
            research_enabled=False,
            analysis_external_processing_allowed=False,
            gemini_enabled=False,
        ),
    )
    result = driver.preflight()
    assert result["blockers"] == ["brave_credential_missing"]
    assert result["provider_requests"] == result["claude_requests"] == 0
    assert result["persistent_research_enabled"] is False
    assert result["persistent_external_ai_processing"] is False
    assert result["search_request_cap"] == result["transport_attempt_cap"] == 1


def test_live_requires_budget_before_configuration_or_database(driver, monkeypatch):
    monkeypatch.setattr(driver, "preflight", lambda: pytest.fail("Budget must be checked first"))
    for budget in (None, 0, -1, 1, float("nan")):
        with pytest.raises(ValueError, match="approval"):
            driver.live(budget)


def test_existing_receipt_prevents_even_database_setup(driver, monkeypatch):
    monkeypatch.setattr(driver, "preflight", lambda: {"blockers": []})
    monkeypatch.setattr(driver, "prepare", lambda: pytest.fail("No database or API retry allowed"))
    (driver.CASE / "live-attempt.json").write_text('{"status":"RESERVED"}')
    with pytest.raises(FileExistsError):
        driver.live(0.05)


def test_exact_original_fact_copy_reaches_retrieval_without_fictionalising_origin(
    driver,
    database,
    research_setup,  # noqa: F811 - imported fixture
):
    settings, csv, _, _ = research_setup
    reports = runner(csv, [])(
        database,
        registry_path=ROOT / "data/dataset_registry.csv",
        policy_path=json.loads(settings.analysis_research_policy.read_text())[
            "acquisition_policy_path"
        ],
        dataset_ids=["D-EMPLOYMENT-SECTOR"],
        enabled=True,
        is_synthetic=False,
    )
    report = driver.check_analysis(database, reports[0]["version_id"])
    assert report["status"] == "RETRIEVED_AND_CITATION_VALIDATED"
    assert report["is_synthetic_association"] and report["model_requests"] == 0
    assert report["workforce_status"] == "insufficient_evidence"
    with database.session_factory() as session:
        copy = session.scalar(
            select(WorkforceObservation).where(WorkforceObservation.is_synthetic.is_(True))
        )
        original = session.get(
            WorkforceObservation,
            UUID(copy.metadata_json["original_observation_id"]),
        )
        reference = session.get(EvidenceReference, copy.evidence_id)
        original_reference = session.get(EvidenceReference, original.evidence_id)
        version = session.get(DatasetVersion, copy.version_id)
        assert copy.value == original.value and copy.period_end == original.period_end
        assert reference.excerpt == original_reference.excerpt
        assert original.is_synthetic is False
        assert version.metadata_json["original_artifact_sha256"] == version.content_sha256
