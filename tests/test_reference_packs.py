"""Frozen genuine, permitted public reference subsets. No network or fabricated facts."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from shiftos.models import DatasetVersion, EvidenceReference, OccupationSkill, SDGReference, Skill
from shiftos.services.evidence.pipeline import run_ingestion

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "dataset,filename,count",
    [
        ("C-ESCO-V103", "esco-v1.0.3.subset.reviewed.json", 87),
        ("F-UN-SDG-RES70-1", "un-sdg-resolution.reviewed.json", 186),
    ],
)
def test_genuine_pack_persists_with_provenance_and_replays(database, dataset, filename, count):
    path = ROOT / "data/reference_packs" / filename
    metadata = json.loads(path.read_text(encoding="utf-8"))["metadata"]
    kwargs = dict(
        registry_path=ROOT / "data/dataset_registry.csv",
        policy_path=ROOT / "data/evidence_acquisition.json",
        dataset_ids=[dataset],
        local_path=path,
        retrieved_at=datetime.fromisoformat(metadata["original_retrieved_at"]),
    )
    first = run_ingestion(database, **kwargs)[0]
    assert first["status"] == "SUCCEEDED", first
    assert first["records_imported"] == count
    assert first["is_synthetic"] is False
    repeat = run_ingestion(database, **kwargs)[0]
    assert repeat["status"] == "UNCHANGED"
    assert repeat["version_id"] == first["version_id"]
    with database.session_factory() as session:
        version = session.scalar(select(DatasetVersion))
        assert version.content_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
        assert session.scalar(select(func.count()).select_from(EvidenceReference)) == count
        if dataset == "C-ESCO-V103":
            assert session.scalar(select(func.count()).select_from(OccupationSkill)) == 39
            assert all(s.description for s in session.scalars(select(Skill)))
            assert all(
                s.metadata_json.get("edition") == "v1.0.3" for s in session.scalars(select(Skill))
            )
        else:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(SDGReference)
                    .where(SDGReference.kind == "goal")
                )
                == 17
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(SDGReference)
                    .where(SDGReference.kind == "target")
                )
                == 169
            )
