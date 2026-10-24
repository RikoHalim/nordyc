"""Portable synthetic snapshots retain frozen outputs and fail closed on unsafe data."""

import copy
import importlib.util
import json
import sys
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from pathways_helpers import seed_pathways
from sqlalchemy import select

from shiftos.core.enums import DocumentFormat, DocumentKind, JobStatus
from shiftos.db.base import Base
from shiftos.db.session import create_database
from shiftos.models import (
    ActionPlanRun,
    CareerRecommendation,
    CareerRun,
    DatasetVersion,
    Document,
    Institution,
    Job,
    Programme,
)
from shiftos.repositories import career, pathways
from shiftos.repositories.catalogue import digest
from shiftos.services.ingestion.worker import run_once

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "programme_transfer_runner", ROOT / "scripts" / "transfer_programme.py"
)
transfer = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = transfer
_spec.loader.exec_module(transfer)


@pytest.fixture(autouse=True)
def no_provider_requests(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Programme transfer must not contact a model or research provider")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.fixture
def prepared_transfer(session, database):
    fixture = seed_pathways(session, database)
    plan = pathways.enqueue_plan(session, fixture.parent.id, fixture.request, fixture.settings)
    assert run_once(database, fixture.settings) == plan.job_id
    session.expire_all()
    fixture.plan = session.get(ActionPlanRun, plan.id)
    assert fixture.plan.result_json
    assert session.get(Job, plan.job_id).status in {JobStatus.SUCCEEDED, JobStatus.PARTIAL}
    assert career.access_state(session, fixture.parent, fixture.settings)[0]
    assert pathways.access_state(session, fixture.plan, fixture.settings)[0]
    return fixture


@pytest.fixture
def empty_destination():
    database = create_database("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(database.engine)
    try:
        yield database
    finally:
        database.engine.dispose()


def snapshot_for(database, fixture):
    with database.engine.connect() as connection:
        return transfer.build_snapshot(connection, fixture.records.programme.id)


def test_roundtrip_preserves_frozen_results_versions_signatures_and_permissions(
    database, session, prepared_transfer, empty_destination
):
    fixture = prepared_transfer
    snapshot = snapshot_for(database, fixture)
    assert snapshot["format"] == "shiftos-programme-transfer-1"
    assert snapshot["programme_id"] == str(fixture.records.programme.id)
    assert transfer.validate_snapshot(snapshot) is None
    assert snapshot["sha256"] == digest(
        {key: value for key, value in snapshot.items() if key != "sha256"}
    )
    # JSON serialization is the real transfer boundary, not shared ORM instances.
    portable = json.loads(json.dumps(snapshot))
    with empty_destination.engine.begin() as connection:
        transfer.restore_rows(connection, portable)
        assert isinstance(transfer.verify_restored(connection, portable), dict)
    with empty_destination.session_factory() as restored:
        parent = restored.get(CareerRun, fixture.parent.id)
        plan = restored.get(ActionPlanRun, fixture.plan.id)
        assert parent.result_json == fixture.parent.result_json
        assert parent.manifest_json == fixture.parent.manifest_json
        assert parent.fingerprint == fixture.parent.fingerprint
        assert plan.result_json == fixture.plan.result_json
        assert plan.manifest_json == fixture.plan.manifest_json
        assert plan.fingerprint == fixture.plan.fingerprint
        for original in fixture.recommendations:
            row = restored.get(CareerRecommendation, original.id)
            assert row.result_json == original.result_json
            assert row.version_sha256 == original.version_sha256
        for run, repository in ((parent, career), (plan, pathways)):
            references = run.manifest_json["packet"]["references"]
            assert (
                repository.source_signatures(restored, references)
                == (run.manifest_json["source_signatures"])
            )
            assert repository.access_state(restored, run, fixture.settings)[0]
        assert {row["is_synthetic"] for row in plan.result_json["evidence"]} == {True, False}
        assert plan.result_json["model"]["request_count"] == 0
        assert plan.result_json["review"].get("automatic_curriculum_change", False) is False
        version = restored.get(DatasetVersion, fixture.records.version.id)
        original = session.get(DatasetVersion, fixture.records.version.id)
        assert version.metadata_json == original.metadata_json
        version.metadata_json = {
            **version.metadata_json,
            "analysis_permissions": {
                "internal_analysis_allowed": False,
                "external_model_allowed": False,
                "excerpt_output_allowed": False,
                "basis": "Explicit synthetic test withdrawal after transfer",
            },
        }
        restored.commit()
        assert not career.access_state(restored, parent, fixture.settings)[0]
        assert not pathways.access_state(restored, plan, fixture.settings)[0]


def test_export_excludes_unrelated_real_programme_and_documents(
    database, session, prepared_transfer
):
    real_institution = Institution(name="Unrelated private institutional fixture")
    session.add(real_institution)
    session.flush()
    real_programme = Programme(
        institution_id=real_institution.id,
        name="Unrelated real-record fixture must never be exported",
    )
    session.add(real_programme)
    session.commit()
    snapshot = snapshot_for(database, prepared_transfer)
    exported = {row["id"] for rows in snapshot["rows"].values() for row in rows}
    assert str(real_programme.id) not in exported
    assert str(real_institution.id) not in exported
    assert len(snapshot["rows"]["programmes"]) == 1
    assert snapshot["rows"]["programmes"][0]["is_synthetic"] is True


def test_export_rejects_a_nonsynthetic_programme(database, session, prepared_transfer):
    programme = prepared_transfer.records.programme
    programme.is_synthetic = False
    session.commit()
    with database.engine.connect() as connection, pytest.raises(transfer.TransferError):
        transfer.build_snapshot(connection, programme.id)


def test_export_rejects_an_unknown_programme(database):
    with database.engine.connect() as connection, pytest.raises(transfer.TransferError):
        transfer.build_snapshot(connection, uuid4())


def test_checksum_tampering_is_rejected_before_destination_writes(
    database, prepared_transfer, empty_destination
):
    snapshot = snapshot_for(database, prepared_transfer)
    snapshot["rows"]["programmes"][0]["name"] = "Tampered fictional programme"
    with pytest.raises(transfer.TransferError):
        transfer.validate_snapshot(snapshot)
    with empty_destination.engine.begin() as connection:
        with pytest.raises(transfer.TransferError):
            transfer.restore_rows(connection, snapshot)
        assert connection.execute(select(Programme.__table__)).all() == []


def test_uncited_raw_document_storage_is_the_only_omission(
    database, session, prepared_transfer, empty_destination
):
    fixture = prepared_transfer
    private_path = "C:/private-transfer-fixture/original-only.pdf"
    document = Document(
        programme_revision_id=fixture.records.revision.id,
        filename="synthetic-uncited-original.pdf",
        document_kind=DocumentKind.PROGRAMME_STRUCTURE,
        format=DocumentFormat.PDF,
        content_sha256="a" * 64,
        parser_version="synthetic-transfer-test-1",
        storage_path=private_path,
        metadata_json={"is_synthetic": True, "original_only": True},
        is_synthetic=True,
    )
    session.add(document)
    session.commit()
    snapshot = snapshot_for(database, fixture)
    exported = next(row for row in snapshot["rows"]["documents"] if row["id"] == str(document.id))
    assert exported["storage_path"] is None
    assert exported["metadata_json"] == document.metadata_json
    assert snapshot["omitted_storage"] == [
        {"table": "documents", "id": str(document.id), "field": "storage_path"}
    ]
    assert private_path not in json.dumps(snapshot)
    assert session.get(Document, document.id).storage_path == private_path
    with empty_destination.engine.begin() as connection:
        transfer.restore_rows(connection, snapshot)
        transfer.verify_restored(connection, snapshot)
    with empty_destination.session_factory() as restored:
        assert restored.get(Document, document.id).storage_path is None
        assert pathways.access_state(
            restored, restored.get(ActionPlanRun, fixture.plan.id), fixture.settings
        )[0]


def test_cited_document_private_path_cannot_be_silently_removed(
    database, session, prepared_transfer
):
    fixture = prepared_transfer
    signed = fixture.parent.manifest_json["source_signatures"]
    document_id = next(UUID(key.split(":", 1)[1]) for key in signed if key.startswith("document:"))
    document = session.get(Document, document_id)
    document.storage_path = "C:/private-transfer-fixture/cited-original.pdf"
    session.commit()
    with database.engine.connect() as connection, pytest.raises(transfer.TransferError):
        transfer.build_snapshot(connection, fixture.records.programme.id)
    assert session.get(Document, document_id).storage_path is not None


def test_restore_refuses_nonempty_destination_without_changing_rows(
    database, prepared_transfer, empty_destination
):
    snapshot = snapshot_for(database, prepared_transfer)
    with empty_destination.session_factory() as destination:
        existing = Institution(name="Pre-existing synthetic target", is_synthetic=True)
        destination.add(existing)
        destination.commit()
        existing_id = existing.id
    with empty_destination.engine.begin() as connection:
        with pytest.raises(transfer.TransferError):
            transfer.restore_rows(connection, snapshot)
        assert connection.execute(select(Institution.__table__.c.id)).scalars().all() == [
            existing_id
        ]
        assert connection.execute(select(Programme.__table__)).all() == []


def test_unknown_table_cannot_be_imported_even_with_a_recomputed_checksum(
    database, prepared_transfer
):
    snapshot = copy.deepcopy(snapshot_for(database, prepared_transfer))
    snapshot["rows"]["unrecognised_private_table"] = [{"id": str(uuid4())}]
    snapshot["sha256"] = digest({key: value for key, value in snapshot.items() if key != "sha256"})
    with pytest.raises(transfer.TransferError):
        transfer.validate_snapshot(snapshot)


def test_completed_upload_before_revision_is_included_by_exact_programme_target(
    database, session, prepared_transfer
):
    programme = prepared_transfer.records.programme
    upload = Job(
        institution_id=programme.institution_id,
        programme_revision_id=None,
        kind="CURRICULUM_PDF_UPLOAD",
        status=JobStatus.SUCCEEDED,
        payload_json={"programme_id": str(programme.id), "content_sha256": "a" * 64},
        is_synthetic=True,
    )
    unrelated = Job(
        institution_id=programme.institution_id,
        kind="CURRICULUM_PDF_UPLOAD",
        status=JobStatus.SUCCEEDED,
        payload_json={"programme_id": str(uuid4())},
        is_synthetic=True,
    )
    session.add_all([upload, unrelated])
    session.commit()
    snapshot = snapshot_for(database, prepared_transfer)
    ids = {row["id"] for row in snapshot["rows"]["jobs"]}
    assert str(upload.id) in ids
    assert str(unrelated.id) not in ids


@pytest.mark.parametrize(
    "value",
    [
        {"gemini_api_key": "a-private-value"},
        {"authorization": "a-private-value"},
        "postgresql://fixture-user:fixture-password@host/fixture-db",
        "C:/private-fixture/original.pdf",
        "/home/runner/private-fixture/original.pdf",
        "https://example.invalid/source?access_token=private-fixture",
    ],
)
def test_private_fields_are_rejected_without_echoing_their_values(value):
    with pytest.raises(transfer.TransferError) as rejected:
        transfer._safe(value)
    assert "private-fixture" not in str(rejected.value)
    assert "a-private-value" not in str(rejected.value)


def test_public_https_source_is_not_misclassified_as_a_windows_path():
    assert transfer._safe("https://example.invalid/synthetic-source") is None
