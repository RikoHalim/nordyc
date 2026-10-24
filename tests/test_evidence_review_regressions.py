"""Offline persistence review regressions; all concept data below is synthetic."""

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from shiftos.models import Source
from shiftos.models.evidence import (
    Dataset,
    DatasetVersion,
    EvidenceIngestionJob,
    EvidenceReference,
    Occupation,
    OccupationSkill,
    Skill,
)
from shiftos.repositories.evidence import load_batch, sync_registry
from shiftos.services.evidence.acquisition import Artifact
from shiftos.services.evidence.parsers import ParsedBatch, ParsedRecord, parse_esco_api
from shiftos.services.evidence.pipeline import run_ingestion
from shiftos.services.evidence.registry import read_registry


def _load(session, batch):
    entry = next(
        row for row in read_registry(Path("data/dataset_registry.csv")) if row.id == "C-ESCO"
    )
    # Registry metadata is used for schema plumbing only; no genuine records here.
    sync_registry(session, [entry])
    dataset = session.scalar(select(Dataset).where(Dataset.registry_key == entry.id))
    content = batch.model_dump_json().encode()
    artifact = Artifact(
        "https://example.invalid/synthetic.json",
        content,
        hashlib.sha256(content).hexdigest(),
        datetime(2026, 10, 20, tzinfo=UTC),
    )
    return load_batch(
        session,
        dataset,
        entry,
        artifact,
        batch,
        parser_version="synthetic-test-1",
        context={"is_synthetic": True},
        is_synthetic=True,
    )


def test_multiple_esco_relationships_have_distinct_persistable_evidence(session) -> None:
    payload = {
        "uri": "https://example.invalid/occupation/synthetic-accountant",
        "className": "Occupation",
        "preferredLabel": {"en": "Synthetic accountant"},
        "_links": {
            "hasEssentialSkill": [
                {
                    "uri": "https://example.invalid/skill/synthetic-ledger",
                    "title": "Synthetic ledger",
                },
                {
                    "uri": "https://example.invalid/skill/synthetic-audit",
                    "title": "Synthetic audit",
                },
            ]
        },
    }
    batch = parse_esco_api(json.dumps(payload).encode())
    _, created, counts = _load(session, batch)
    session.commit()
    assert created is True
    assert counts["occupation_skill"] == 2
    assert session.scalar(select(func.count()).select_from(OccupationSkill)) == 2


def test_pdf_candidate_text_and_tables_survive_persistence(session) -> None:
    text = ("Synthetic unreviewed document text " * 100).strip()
    tables = [[["Synthetic category", "Synthetic value"], ["Synthetic row", "1"]]]
    batch = ParsedBatch(
        records=[
            ParsedRecord(
                kind="pdf_candidate",
                key="page:1",
                locator="PDF page 1",
                excerpt=text[:2000],
                page_number=1,
                review_status="needs_review",
                data={"text": text, "tables": tables},
            )
        ]
    )
    _, created, counts = _load(session, batch)
    session.commit()
    assert created is True
    assert counts["pdf_candidate"] == 1
    reference = session.scalar(select(EvidenceReference))
    assert reference.review_status == "needs_review"
    assert reference.metadata_json["extraction_candidate"]["text"] == text
    assert reference.metadata_json["extraction_candidate"]["tables"] == tables


def _manual_record(kind, key, data):
    return {
        "kind": kind,
        "key": key,
        "data": data,
        "locator": f"Synthetic fixture {kind} {key}",
        "excerpt": f"Synthetic fixture record {key}",
        "review_status": "reviewed",
    }


def _synthetic_records():
    return [
        _manual_record(
            "occupation", "synthetic-role", {"taxonomy": "synthetic", "label": "Synthetic role"}
        ),
        _manual_record(
            "skill", "synthetic-skill", {"taxonomy": "synthetic", "label": "Synthetic skill"}
        ),
        _manual_record(
            "occupation_skill",
            "synthetic-mapping",
            {
                "occupation_external_id": "synthetic-role",
                "skill_external_id": "synthetic-skill",
                "relationship": "essential",
            },
        ),
    ]


def _manual_pipeline(database, tmp_path, records):
    """Exercise a real registry entry's plumbing with explicitly synthetic content."""
    content = tmp_path / "evidence.synthetic.json"
    content.write_text(json.dumps({"reviewed": True, "records": records}), encoding="utf-8")
    policy = tmp_path / "policy.synthetic.json"
    policy.write_text(
        json.dumps(
            {
                "C-ESCO": {
                    "adapter": "reviewed_json",
                    "format": "json",
                    "reuse_reviewed": True,
                    "instructions": "Synthetic offline test only; no publisher acquisition",
                }
            }
        ),
        encoding="utf-8",
    )
    return run_ingestion(
        database,
        policy_path=policy,
        dataset_ids=["C-ESCO"],
        local_path=content,
        retrieved_at=datetime(2026, 10, 20, tzinfo=UTC),
        is_synthetic=True,
    )[0]


@pytest.mark.parametrize("missing", ["occupation_external_id", "skill_external_id"])
def test_unmatched_mapping_fails_atomically_without_source_or_partial_facts(
    database, tmp_path, missing
) -> None:
    records = _synthetic_records()
    records[2]["data"][missing] = "synthetic-absent-classification"
    report = _manual_pipeline(database, tmp_path, records)
    assert report["status"] == "FAILED"
    assert report["records_imported"] == 0
    with database.session_factory() as session:
        for model in (
            DatasetVersion,
            Source,
            EvidenceReference,
            Occupation,
            Skill,
            OccupationSkill,
        ):
            assert session.scalar(select(func.count()).select_from(model)) == 0
        assert session.scalar(select(EvidenceIngestionJob.status)) == "FAILED"


def test_duplicate_relationships_and_repeat_pipeline_import_are_idempotent(
    database, tmp_path
) -> None:
    records = _synthetic_records()
    records.append(deepcopy(records[2]))
    first = _manual_pipeline(database, tmp_path, records)
    second = _manual_pipeline(database, tmp_path, records)
    assert first["status"] == "SUCCEEDED", first
    assert first["records_imported"] == 3
    assert second["status"] == "UNCHANGED", second
    assert second["records_imported"] == 0
    assert first["version_id"] == second["version_id"]
    assert "Removed 1 exact duplicate source records" in first["warnings"]
    with database.session_factory() as session:
        for model in (DatasetVersion, Source, Occupation, Skill, OccupationSkill):
            assert session.scalar(select(func.count()).select_from(model)) == 1
        assert session.scalar(select(func.count()).select_from(EvidenceReference)) == 3


def test_conflicting_duplicate_fails_before_any_facts_are_loaded(database, tmp_path) -> None:
    records = _synthetic_records()
    changed = deepcopy(records[0])
    changed["data"]["label"] = "Synthetic conflicting label"
    records.append(changed)
    report = _manual_pipeline(database, tmp_path, records)
    assert report["status"] == "FAILED"
    with database.session_factory() as session:
        for model in (DatasetVersion, Source, Occupation, Skill, OccupationSkill):
            assert session.scalar(select(func.count()).select_from(model)) == 0
