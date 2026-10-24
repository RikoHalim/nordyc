"""Controlled evaluation observations; all academic/model inputs remain fictional."""

from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from pathways_helpers import seed_pathways

from shiftos.services.evaluation import evaluate_reports, load_collection
from shiftos.services.pathways.engine import evaluate

COLLECTION = Path(__file__).resolve().parents[1] / "examples/evaluation/collection.v1.json"


@pytest.fixture
def collection():
    return load_collection(COLLECTION)


@pytest.fixture
def observed_report(session, database, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Synthetic evaluation must not contact external services")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    fixture = seed_pathways(session, database)
    plan = evaluate(session, fixture.parent.id, fixture.request, fixture.settings, fixture.now)
    # This unit fixture evaluates actual engine outputs, not an invented integration
    # receipt. Phase 4/API and replay checks are consequently not_observed here.
    return {
        "responses": {
            "career": {"result_json": fixture.parent.result_json},
            "plan": {"result_json": plan.model_dump(mode="json")},
        },
        "labels": {
            "skills": {key: str(value.id) for key, value in fixture.records.skills.items()},
            "courses": {key: str(value.id) for key, value in fixture.records.courses.items()},
        },
        "replay": {},
    }


def test_collection_has_distinct_labelled_discipline_evidence(collection):
    assert collection.is_synthetic
    assert set(collection.disciplines) == {"computing", "accounting", "biotechnology"}
    for discipline, profile in collection.disciplines.items():
        assert profile["is_synthetic"] is True
        assert profile["discipline"] == discipline
        assert len(profile["occupations"]) == 3
        assert any(row["quote"] is None for row in profile["courses"])
    accounting = str(collection.disciplines["accounting"])
    biotechnology = str(collection.disciplines["biotechnology"])
    assert "ledger" in accounting and "SQL construction" not in accounting
    assert "aseptic" in biotechnology and "SQL construction" not in biotechnology


def test_unexecuted_cases_never_become_successful_metrics(collection):
    report = evaluate_reports(collection, {})
    assert all(row.status == "not_observed" for row in report.observations)
    assert all(row.denominator == 0 and row.pass_rate is None for row in report.metrics)
    assert not report.academic_accuracy_claim
    assert report.live_provider_requests == 0


def test_actual_validators_reject_forgery_and_preserve_labelled_states(collection, observed_report):
    report = evaluate_reports(collection, {"computing": observed_report})
    executed = [row for row in report.observations if row.status != "not_observed"]
    assert len(executed) >= 20
    assert all(row.status == "pass" for row in executed), [
        row.model_dump() for row in executed if row.status == "fail"
    ]
    assert {
        "fabricated_quote",
        "unsupported_action",
        "wrong_relation",
        "wrong_revision",
        "outdated_review",
        "malformed_output",
        "injected_instruction",
        "exposure_replacement",
        "unrelated_sdg",
        "automatic_approval",
        "forecast_probability",
    } <= {row.case_id for row in executed if row.method == "output_mutation"}


def test_broken_baseline_cannot_inflate_mutation_rejection_metrics(collection, observed_report):
    observed_report["responses"]["career"]["result_json"]["programme_id"] = []
    report = evaluate_reports(collection, {"computing": observed_report})
    rows = [row for row in report.observations if row.discipline == "computing"]
    assert next(row for row in rows if row.case_id == "valid_career").status == "fail"
    assert next(row for row in rows if row.case_id == "fabricated_quote").status == "fail"


def test_metrics_use_actual_executed_denominators_and_stable_collection_digest(
    collection, observed_report
):
    first = evaluate_reports(collection, {"computing": observed_report})
    second = evaluate_reports(collection, {"computing": deepcopy(observed_report)})
    assert first == second
    for metric in first.metrics:
        rows = [row for row in first.observations if row.dimension == metric.dimension]
        assert metric.denominator == sum(row.status != "not_observed" for row in rows)
        assert metric.not_observed == sum(row.status == "not_observed" for row in rows)
    changed = collection.model_copy(deep=True)
    changed.version = "1.0.1"
    assert evaluate_reports(changed, {}).collection_sha256 != first.collection_sha256


def test_failed_or_missing_replay_stays_visible_without_source_or_secret_text(
    collection, observed_report
):
    observed_report["replay"] = {
        "source_withdrawn": {"status": "fail", "observed": "SECRET-CANARY-NOT-REPORTABLE"}
    }
    result = evaluate_reports(collection, {"computing": observed_report})
    row = next(
        row
        for row in result.observations
        if row.discipline == "computing" and row.case_id == "withdrawal"
    )
    assert row.status == "fail"
    assert "SECRET-CANARY" not in result.model_dump_json()


def test_false_label_is_detected_instead_of_recording_expected_fixture_as_result(
    collection, observed_report
):
    changed = collection.model_copy(deep=True)
    changed.disciplines["computing"]["expected_states"]["governance"] = "supported"
    result = evaluate_reports(changed, {"computing": observed_report})
    assert (
        next(
            row
            for row in result.observations
            if row.discipline == "computing" and row.case_id == "classification"
        ).status
        == "fail"
    )
