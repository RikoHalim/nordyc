"""Offline synthetic observations test calculations, never real workforce claims."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from test_migrations import migration_database  # noqa: F401 - shared isolated PostgreSQL fixture

from alembic import command
from shiftos.core.config import Settings
from shiftos.db.session import Database
from shiftos.main import create_app
from shiftos.models import (
    AIImpactEvidence,
    Dataset,
    DatasetVersion,
    EvidenceReference,
    Occupation,
    Source,
    WorkforceObservation,
)
from shiftos.schemas.workforce_radar import TrendPolicy
from shiftos.services.evidence.pipeline import run_ingestion
from shiftos.services.evidence.trends import compare_observations, occupation_ai_transformation


@pytest.fixture
def radar_records(session):
    source = Source(
        publisher="Synthetic Radar Publisher",
        title="Synthetic radar fixture",
        url="https://example.invalid/synthetic-radar",
        is_synthetic=True,
        evidence_class="synthetic_demo",
    )
    dataset = Dataset(
        registry_key="SYNTHETIC-RADAR",
        name="Synthetic Radar Dataset",
        category="synthetic_demo",
        is_synthetic=True,
    )
    session.add_all([source, dataset])
    session.flush()
    versions, references, occupations, observations = [], [], [], []
    for index in range(2):
        version = DatasetVersion(
            dataset_id=dataset.id,
            source_id=source.id,
            content_sha256=str(index) * 64,
            parser_version="synthetic-radar-v1",
            retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
            publication_date="2026-07" if index == 0 else "2026-08-15",
            artifact_url=source.url,
            is_synthetic=True,
        )
        session.add(version)
        session.flush()
        reference = EvidenceReference(
            version_id=version.id,
            locator="Synthetic test table",
            excerpt="Invented test count",
            page_number=1,
            review_status="reviewed",
            is_synthetic=True,
        )
        session.add(reference)
        session.flush()
        occupation = Occupation(
            version_id=version.id,
            evidence_id=reference.id,
            external_id="synthetic:accountant",
            taxonomy="SYNTHETIC",
            classification_code="SYNTHETIC-1234",
            label="Synthetic accountant",
            is_synthetic=True,
        )
        session.add(occupation)
        session.flush()
        observation = WorkforceObservation(
            version_id=version.id,
            evidence_id=reference.id,
            external_id=f"synthetic:quarter:{index}",
            occupation_id=occupation.id,
            occupation_label=occupation.label,
            classification_system="SYNTHETIC",
            classification_code=occupation.classification_code,
            sector="synthetic cross-sector",
            geography="MY",
            period_start=date(2026, 1 + 3 * index, 1),
            period_end=date(2026, 3, 31) if index == 0 else date(2026, 6, 30),
            indicator="job_postings",
            value=Decimal(100 + index * 20),
            unit="postings",
            metadata_json={
                "series_id": "synthetic:postings",
                "population_level": "occupation",
                "population": "synthetic eligible population",
                "sex": "all",
                "methodology": "synthetic complete sample",
            },
            is_synthetic=True,
        )
        session.add(observation)
        versions.append(version)
        references.append(reference)
        occupations.append(occupation)
        observations.append(observation)
    session.commit()
    return {
        "source": source,
        "dataset": dataset,
        "versions": versions,
        "references": references,
        "occupations": occupations,
        "before": observations[0],
        "after": observations[1],
    }


def _compare(session, records, **policy):
    return compare_observations(
        session,
        records["before"].id,
        records["after"].id,
        TrendPolicy(**policy),
    )


def _ai(session, records, **overrides):
    values = {
        "version_id": records["versions"][1].id,
        "evidence_id": records["references"][1].id,
        "external_id": f"synthetic:ai:{uuid4()}",
        "occupation_id": records["occupations"][1].id,
        "occupation_label": "Synthetic accountant",
        "task": "Synthetic reporting task",
        "capability": "Synthetic documented capability",
        "statement": "Invented observed change",
        "impact_type": "observed_practice",
        "limitations": "Synthetic limited experiment",
        "is_synthetic": True,
    }
    values.update(overrides)
    row = AIImpactEvidence(**values)
    session.add(row)
    session.commit()
    return row


@pytest.mark.parametrize(
    "value,classification,absolute,percent",
    [
        (120, "RISING", 20, 20),
        (80, "DECLINING", -20, -20),
        (104, "STABLE", 4, 4),
        (100, "STABLE", 0, 0),
        (105, "RISING", 5, 5),
        (95, "DECLINING", -5, -5),
    ],
)
def test_observed_direction_thresholds_and_exact_changes(
    session,
    radar_records,
    value,
    classification,
    absolute,
    percent,
):
    radar_records["after"].value = Decimal(value)
    result = _compare(session, radar_records)
    assert result.classification == classification
    assert result.absolute_change == absolute
    assert result.percentage_change == percent
    assert result.compatible is True
    assert result.time_horizon == "short_term"
    assert result.sustained_trend_supported is False
    assert result.is_synthetic is True
    assert result.ai_transformation.is_ai_transforming is None


def test_configurable_absolute_and_percentage_gates(session, radar_records):
    assert _compare(session, radar_records, absolute_threshold=21).classification == "STABLE"
    assert _compare(session, radar_records, percent_threshold=21).classification == "STABLE"
    assert (
        _compare(session, radar_records, absolute_threshold=20, percent_threshold=20).classification
        == "RISING"
    )
    radar_records["after"].value = Decimal(100)
    assert (
        _compare(session, radar_records, absolute_threshold=0, percent_threshold=0).classification
        == "STABLE"
    )


@pytest.mark.parametrize(
    "before,after,status,classification,absolute",
    [
        (0, 20, "zero", "INSUFFICIENT_DATA", 20),
        (0, 0, "zero", "STABLE", 0),
        (None, 20, "missing", "INSUFFICIENT_DATA", None),
        (100, None, "missing", "INSUFFICIENT_DATA", None),
        (-1, 20, "invalid", "INSUFFICIENT_DATA", None),
    ],
)
def test_zero_missing_and_invalid_values(
    session,
    radar_records,
    before,
    after,
    status,
    classification,
    absolute,
):
    radar_records["before"].value = before
    radar_records["after"].value = after
    result = _compare(session, radar_records)
    assert result.baseline_status == status
    assert result.classification == classification
    assert result.absolute_change == absolute
    assert result.percentage_change is None


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("geography", "SG", "incompatible_geography"),
        ("unit", "employees", "incompatible_unit"),
        ("indicator", "employment_count", "incompatible_indicator"),
        ("sector", "synthetic new sector", "incompatible_sector"),
        ("classification_system", "SYNTHETIC-V2", "incompatible_classification_system"),
        ("classification_code", "SYNTHETIC-OTHER", "incompatible_classification_code"),
        ("occupation_label", "Synthetic biologist", "incompatible_occupation_label"),
    ],
)
def test_incompatible_published_dimensions(session, radar_records, field, value, reason):
    setattr(radar_records["after"], field, value)
    result = _compare(session, radar_records)
    assert result.classification == "INSUFFICIENT_DATA"
    assert result.compatible is False
    assert reason in result.reasons
    assert result.absolute_change is None


@pytest.mark.parametrize(
    "key,value",
    [
        ("sex", "female"),
        ("population", "different population"),
        ("population_level", "occupation_group"),
        ("source_granularity", "group"),
        ("classification_version", "new-edition"),
        ("methodology", "different platform"),
        ("series_id", "synthetic:new-series"),
        ("dimensions", {"contract": "part-time"}),
    ],
)
def test_incompatible_metadata_dimensions(session, radar_records, key, value):
    row = radar_records["after"]
    row.metadata_json = {**row.metadata_json, key: value}
    result = _compare(session, radar_records)
    assert result.classification == "INSUFFICIENT_DATA"
    assert f"incompatible_{key}" in result.reasons


@pytest.mark.parametrize(
    "start,end,period_type",
    [
        (date(2026, 4, 1), date(2026, 4, 30), None),
        (date(2026, 4, 1), date(2026, 6, 29), None),
        (date(2026, 4, 1), date(2026, 6, 30), "year"),
        (date(2026, 1, 1), date(2026, 3, 31), None),
    ],
)
def test_period_duration_or_chronology_incompatibility(
    session, radar_records, start, end, period_type
):
    row = radar_records["after"]
    row.period_start, row.period_end = start, end
    row.metadata_json = {**row.metadata_json, "period_type": period_type}
    assert _compare(session, radar_records).classification == "INSUFFICIENT_DATA"


def test_leap_year_annual_periods_are_compatible_but_never_sustained(session, radar_records):
    radar_records["before"].period_start = date(2024, 1, 1)
    radar_records["before"].period_end = date(2024, 12, 31)
    radar_records["after"].period_start = date(2025, 1, 1)
    radar_records["after"].period_end = date(2025, 12, 31)
    result = _compare(session, radar_records)
    assert result.compatible is True
    assert result.classification == "RISING"
    assert result.time_horizon == "two_period_comparison"
    assert result.period_type == "year"
    assert result.sustained_trend_supported is False


def test_broad_dosm_group_compares_without_individual_occupation_or_ai_claim(
    session, radar_records
):
    for row, version in zip(
        [radar_records["before"], radar_records["after"]], radar_records["versions"], strict=True
    ):
        row.occupation_id = None
        row.occupation_label = "Professionals"
        row.classification_system = row.classification_code = None
        row.indicator = "online_job_offerings"
        row.metadata_json = {"raw_label": "Professionals", "table_title": "Synthetic Table 2"}
        version.metadata_json = {"transform": {"adapter": "dosm_jmi"}}
    result = _compare(session, radar_records)
    assert result.classification == "RISING"
    assert result.population_level == "occupation_group"
    assert result.measurement_kind == "job_advertising"
    assert result.ai_transformation.is_ai_transforming is None
    assert any("individual occupation" in limitation for limitation in result.limitations)


def test_sector_employment_share_change_is_not_occupational_demand(session, radar_records):
    for row, version in zip(
        [radar_records["before"], radar_records["after"]], radar_records["versions"], strict=True
    ):
        row.occupation_id = None
        row.occupation_label = None
        row.indicator, row.unit = "employment_distribution", "percent"
        row.value = Decimal("20") if row is radar_records["before"] else Decimal("22")
        row.metadata_json = {"sex": "all"}
        version.metadata_json = {"transform": {"adapter": "employment_sector"}}
    result = _compare(session, radar_records)
    assert result.classification == "INSUFFICIENT_DATA"
    assert result.measurement_kind == "employment_share"
    assert result.absolute_change == 2
    assert result.percentage_change == 10
    assert result.population_level == "sector"


@pytest.mark.parametrize("impact_type", ["observed_practice", "observed_capability"])
@pytest.mark.parametrize("after,classification", [(120, "RISING"), (80, "DECLINING")])
def test_ai_transformation_is_independent_of_direction(
    session,
    radar_records,
    impact_type,
    after,
    classification,
):
    _ai(session, radar_records, impact_type=impact_type)
    radar_records["after"].value = after
    result = _compare(session, radar_records)
    assert result.classification == classification
    assert result.ai_transformation.status == "AI-TRANSFORMING"
    assert result.ai_transformation.is_ai_transforming is True
    assert result.ai_transformation.evidence[0].supports_transformation is True


@pytest.mark.parametrize("impact_type", ["occupational_exposure", "future_prediction"])
def test_exposure_and_predictions_never_activate_transformation(
    session, radar_records, impact_type
):
    _ai(session, radar_records, impact_type=impact_type)
    result = occupation_ai_transformation(session, radar_records["occupations"][1].id)
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.is_ai_transforming is None
    assert result.evidence[0].supports_transformation is False


@pytest.mark.parametrize(
    "problem", ["unreviewed", "no_task", "no_capability", "unknown_date", "correction"]
)
def test_incomplete_ai_evidence_does_not_activate_transformation(session, radar_records, problem):
    row = _ai(session, radar_records)
    if problem == "unreviewed":
        radar_records["references"][1].review_status = "needs_review"
    if problem == "no_task":
        row.task = None
    if problem == "no_capability":
        row.capability = None
    if problem == "unknown_date":
        radar_records["versions"][1].publication_date = "Unknown"
    if problem == "correction":
        row.metadata_json = {"correction_pending": True}
    result = occupation_ai_transformation(session, radar_records["occupations"][1].id)
    assert result.is_ai_transforming is None
    assert result.evidence[0].exclusion_reasons


def test_exact_reviewed_metadata_match_and_conflict_handling(session, radar_records):
    row = _ai(
        session,
        radar_records,
        occupation_id=None,
        metadata_json={"occupation_match_reviewed": True},
    )
    occupation = radar_records["occupations"][1]
    assert occupation_ai_transformation(session, occupation.id).is_ai_transforming is True
    row.metadata_json = {"occupation_match_reviewed": False}
    assert occupation_ai_transformation(session, occupation.id).is_ai_transforming is None
    row.metadata_json = {"occupation_match_reviewed": True, "classification_system": "OTHER"}
    assert occupation_ai_transformation(session, occupation.id).is_ai_transforming is None
    row.occupation_label = "Another exact published label"
    row.metadata_json = {
        "occupation_match_reviewed": True,
        "occupation_taxonomy": occupation.taxonomy,
        "occupation_external_id": occupation.external_id,
    }
    result = occupation_ai_transformation(session, occupation.id)
    assert result.is_ai_transforming is True
    assert result.evidence[0].match_basis == "reviewed_exact_taxonomy_and_identifier"


def test_reproducibility_fingerprint_and_original_source_provenance(session, radar_records):
    original = _compare(session, radar_records)
    repeated = _compare(session, radar_records)
    assert original.model_dump() == repeated.model_dump()
    assert original.before.observation.id == radar_records["before"].id
    assert original.after.version.content_sha256 == "1" * 64
    assert original.before.version.publication_date == "2026-07"
    assert original.after.source.url == radar_records["source"].url
    assert original.before.evidence.page_number == 1
    assert (
        original.fingerprint != _compare(session, radar_records, percent_threshold=50).fingerprint
    )
    radar_records["after"].value = Decimal(130)
    assert _compare(session, radar_records).fingerprint != original.fingerprint
    assert session.scalar(select(func.count()).select_from(WorkforceObservation)) == 2


def test_percentage_calculation_does_not_depend_on_global_decimal_context(session, radar_records):
    radar_records["before"].value = Decimal(3)
    radar_records["after"].value = Decimal(4)
    with localcontext() as context:
        context.prec = 6
        first = _compare(session, radar_records)
    with localcontext() as context:
        context.prec = 20
        second = _compare(session, radar_records)
    assert first.percentage_change == second.percentage_change
    assert first.fingerprint == second.fingerprint


def test_radar_api_and_independent_ai_api(client: TestClient, radar_records, session):
    _ai(session, radar_records)
    query = f"before_id={radar_records['before'].id}&after_id={radar_records['after'].id}"
    response = client.get("/api/v1/evidence/workforce-trends?" + query)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["classification"] == "RISING"
    assert Decimal(data["percentage_change"]) == 20
    assert data["ai_transformation"]["status"] == "AI-TRANSFORMING"
    assert data["sustained_trend_supported"] is False
    assert data["before"]["observation"]["is_synthetic"] is True
    assert client.get("/api/v1/evidence/workforce-trends?" + query).json() == data
    changed = client.get(
        "/api/v1/evidence/workforce-trends?" + query + "&percent_threshold=50"
    ).json()
    assert changed["classification"] == "STABLE"
    path = f"/api/v1/evidence/occupations/{radar_records['occupations'][1].id}/ai-transformation"
    assert client.get(path).json()["is_ai_transforming"] is True


@pytest.mark.parametrize(
    "query",
    [
        "",
        "before_id=bad&after_id=bad",
        "percent_threshold=-1",
        "percent_threshold=NaN",
        "absolute_threshold=Infinity",
    ],
)
def test_radar_api_rejects_invalid_requests(client, radar_records, query):
    base = f"before_id={radar_records['before'].id}&after_id={radar_records['after'].id}"
    response = client.get(
        "/api/v1/evidence/workforce-trends?" + (base + "&" + query if query else "")
    )
    assert response.status_code == 422


def test_radar_api_missing_observations_and_occupations(client):
    query = f"before_id={uuid4()}&after_id={uuid4()}"
    response = client.get("/api/v1/evidence/workforce-trends?" + query)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert (
        client.get(f"/api/v1/evidence/occupations/{uuid4()}/ai-transformation").status_code == 404
    )


def test_missing_series_unknown_granularity_and_suppression_abstain(session, radar_records):
    for row in (radar_records["before"], radar_records["after"]):
        row.occupation_id = None
        row.metadata_json = {}
    result = _compare(session, radar_records)
    assert result.classification == "INSUFFICIENT_DATA"
    assert "missing_series_identity" in result.reasons
    assert "unknown_population_granularity" in result.reasons
    for row in (radar_records["before"], radar_records["after"]):
        row.metadata_json = {"series_id": "synthetic", "population_level": "occupation_group"}
    radar_records["after"].value_status = "suppressed"
    result = _compare(session, radar_records)
    assert result.classification == "INSUFFICIENT_DATA"
    assert "unpublished_or_suppressed_value" in result.reasons
    assert result.absolute_change is None


def test_advertisements_and_actual_employment_remain_distinct(session, radar_records):
    for row in (radar_records["before"], radar_records["after"]):
        row.indicator, row.unit = "employment_count", "employees"
    result = _compare(session, radar_records)
    assert result.classification == "RISING"
    assert result.measurement_kind == "employment"
    assert any("not job postings" in text for text in result.limitations)


@pytest.mark.parametrize(
    "problem,reason",
    [
        ("retrieval", "observation_period_after_retrieval"),
        ("publication", "observation_period_after_publication"),
    ],
)
def test_future_period_relative_to_source_assertion_is_not_observed_change(
    session,
    radar_records,
    problem,
    reason,
):
    version = radar_records["versions"][1]
    if problem == "retrieval":
        version.retrieved_at = datetime(2026, 6, 1, tzinfo=UTC)
    else:
        version.publication_date = "2026-06-01"
    result = _compare(session, radar_records)
    assert result.classification == "INSUFFICIENT_DATA"
    assert result.absolute_change is None
    assert reason in result.reasons


@pytest.mark.parametrize(
    "bad_field,bad_value",
    [
        ("population_level", ["occupation"]),
        ("series_id", {"invalid": "object"}),
    ],
)
def test_malformed_interpreted_metadata_abstains_instead_of_crashing(
    session,
    radar_records,
    bad_field,
    bad_value,
):
    for row in (radar_records["before"], radar_records["after"]):
        row.metadata_json = {**row.metadata_json, bad_field: bad_value}
    result = _compare(session, radar_records)
    assert result.classification == "INSUFFICIENT_DATA"
    assert result.compatible is False
    assert any(reason.startswith("malformed_") for reason in result.reasons)


def test_trend_has_no_ai_downcast_from_a_group(session, radar_records):
    _ai(session, radar_records)
    for row in (radar_records["before"], radar_records["after"]):
        row.metadata_json = {**row.metadata_json, "population_level": "occupation_group"}
    result = _compare(session, radar_records)
    assert result.ai_transformation.is_ai_transforming is None


@pytest.mark.integration
def test_postgresql_offline_import_replay_and_radar_http(
    migration_database,  # noqa: F811 - imported fixture
    tmp_path,
):
    """Genuine PostgreSQL execution with entirely invented test input and no network."""
    connection, config = migration_database
    command.upgrade(config, "head")
    connection.commit()
    database = Database(connection.engine, sessionmaker(bind=connection, expire_on_commit=False))
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "fixtures/evidence/records.synthetic.json").read_text())
    for record in payload["records"]:
        if record["kind"] == "workforce":
            record["data"]["indicator"] = "job_postings"
            record["data"]["unit"] = "synthetic_postings"
            record["data"]["metadata_json"] = {
                "series_id": "synthetic-postings",
                "population_level": "occupation",
            }
    path = tmp_path / "radar.synthetic.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    arguments = dict(
        registry_path=root / "fixtures/evidence/dataset_registry.synthetic.csv",
        policy_path=root / "fixtures/evidence/policy.synthetic.json",
        dataset_ids=["SYNTHETIC-EVIDENCE"],
        local_path=path,
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        is_synthetic=True,
    )
    first = run_ingestion(database, **arguments)[0]
    repeated = run_ingestion(database, **arguments)[0]
    assert first["status"] == "SUCCEEDED", first
    assert repeated["status"] == "UNCHANGED", repeated
    assert first["version_id"] == repeated["version_id"]
    with database.session_factory() as session:
        rows = session.scalars(
            select(WorkforceObservation).order_by(WorkforceObservation.period_start)
        ).all()
        assert len(rows) == 2
        assert session.scalar(select(func.count()).select_from(DatasetVersion)) == 1
        before_id, after_id = rows[0].id, rows[1].id
    settings = Settings(_env_file=None, app_env="test")
    with TestClient(create_app(settings=settings, database=database)) as client:
        query = f"before_id={before_id}&after_id={after_id}"
        response = client.get("/api/v1/evidence/workforce-trends?" + query)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["classification"] == "RISING"
        assert Decimal(result["percentage_change"]) == 20
        assert result["population_level"] == "occupation"
        assert result["is_synthetic"] is True
        assert result["before"]["version"]["id"] == first["version_id"]
        assert result["before"]["source"]["evidence_class"] == "synthetic_demo"
        assert (
            result["fingerprint"]
            == client.get("/api/v1/evidence/workforce-trends?" + query).json()["fingerprint"]
        )
