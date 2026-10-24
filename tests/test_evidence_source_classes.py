"""Synthetic test contents exercise retention of genuine registry evidence classes."""

import hashlib
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from shiftos.models import Source
from shiftos.models.evidence import AIImpactEvidence, Dataset
from shiftos.repositories.evidence import EvidenceLoadError, load_batch, sync_registry
from shiftos.services.evidence.acquisition import Artifact
from shiftos.services.evidence.parsers import ParsedBatch, ParsedRecord
from shiftos.services.evidence.registry import read_registry


@pytest.mark.parametrize(
    "impact,capability,allowed",
    [
        ("occupational_exposure", None, True),
        ("observed_capability", "Synthetic capability", False),
        ("future_prediction", None, False),
        ("occupational_exposure", "Synthetic capability", False),
    ],
)
def test_workforce_source_can_supply_context_not_measured_ai_capability(
    session, impact, capability, allowed
):
    entry = next(e for e in read_registry("data/dataset_registry.csv") if e.id == "E-OECD-2024")
    sync_registry(session, [entry])
    dataset = session.scalar(select(Dataset).where(Dataset.registry_key == entry.id))
    batch = ParsedBatch(
        records=[
            ParsedRecord(
                kind="ai_evidence",
                key="synthetic-context",
                data={
                    "statement": "Synthetic contextual exposure assertion for validation only",
                    "impact_type": impact,
                    "capability": capability,
                    "limitations": "Synthetic test input",
                },
                locator="Synthetic test locator",
                excerpt="Synthetic test excerpt",
            )
        ]
    )
    artifact = Artifact(
        entry.source_url,
        b"synthetic",
        hashlib.sha256(b"synthetic").hexdigest(),
        datetime(2026, 10, 1, tzinfo=UTC),
    )
    if allowed:
        load_batch(
            session, dataset, entry, artifact, batch, parser_version="synthetic-test", context={}
        )
        assert session.scalar(select(Source.evidence_class)) == "dated_workforce_signal"
        assert session.scalar(select(AIImpactEvidence.impact_type)) == "occupational_exposure"
    else:
        with pytest.raises(EvidenceLoadError, match="source evidence class"):
            load_batch(
                session,
                dataset,
                entry,
                artifact,
                batch,
                parser_version="synthetic-test",
                context={},
            )
