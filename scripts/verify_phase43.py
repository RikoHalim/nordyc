"""One separately approved Brave search through the existing research pipeline.

Preflight is non-billable. Live execution uses an exclusively reserved receipt,
one query, one HTTP attempt, one registered original, no model calls and only the
owned Phase 4.2 loopback PostgreSQL cluster. No shared settings are changed.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from phase42_database import ROOT, URL, prepare

sys.path.insert(0, str(ROOT / "src"))
CASE = ROOT / "data/local/phase43-verification"
DATASET = "D-EMPLOYMENT-SECTOR"
QUERY = "site:open.dosm.gov.my Malaysia employment sector statistics"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def configuration():
    from shiftos.core.config import Settings

    return Settings(_env_file=None, database_url=URL)


def preflight():
    from shiftos.services.analysis.providers import BRAVE_ENDPOINT
    from shiftos.services.analysis.research import ResearchService
    from shiftos.services.evidence.acquisition import DatasetFetcher

    config = configuration()
    # Reading this configuration neither creates a DB connection nor sends a request.
    service = ResearchService(None, config)
    policy, entries, rules, rights, policy_hash = service._configuration()
    entry = next(row for row in entries if row.id == DATASET)
    rule = rules[DATASET]
    permission = rights[DATASET]
    source_allowed = (
        DATASET in policy.allowed_dataset_ids
        and entry.verification_status == "Verified"
        and rule.access_reviewed
        and rule.reuse_reviewed
        and all(
            permission.get(key) is True
            for key in (
                "internal_analysis_allowed",
                "external_model_allowed",
                "excerpt_output_allowed",
            )
        )
        and "storage.dosm.gov.my" in DatasetFetcher.reviewed_hosts
        and not policy.search_result_storage_allowed
    )
    blockers = []
    if not config.brave_search_api_key:
        blockers.append("brave_credential_missing")
    if not source_allowed:
        blockers.append("source_or_storage_policy_requires_review")
    report = {
        "status": "BLOCKED" if blockers else "READY_FOR_SEPARATE_LIVE_APPROVAL",
        "blockers": blockers,
        "brave_key_present": bool(config.brave_search_api_key),
        "persistent_research_enabled": config.research_enabled,
        "persistent_external_ai_processing": config.analysis_external_processing_allowed,
        "endpoint": BRAVE_ENDPOINT,
        "query": QUERY,
        "query_category": "workforce",
        "search_request_cap": 1,
        "transport_attempt_cap": 1,
        "timeout_seconds": 20,
        "research_timeout_seconds": 60,
        "original_document_cap": 1,
        "original_max_bytes": 5_000_000,
        "source_dataset": DATASET,
        "original_url": entry.download_api_url,
        "source_policy_sha256": policy_hash,
        "search_result_storage_allowed": False,
        "provider_requests": 0,
        "claude_requests": 0,
        "gemini_requests": 0,
        "observed_cost": None,
    }
    CASE.mkdir(parents=True, exist_ok=True)
    write_json(CASE / "preflight.json", report)
    return report


def check_analysis(database, version_id):
    """Copy one exact public observation into an explicitly synthetic test lane.

    Original source records remain non-synthetic and unchanged. The copied facts
    retain their real identities/dates/hash; the fictional course and association
    are synthetic. This runs retrieval and original validation, never a model.
    """
    from sqlalchemy import select

    from shiftos.models import (
        Course,
        DatasetVersion,
        EvidenceReference,
        Institution,
        Programme,
        ProgrammeRevision,
        Source,
        WorkforceObservation,
    )
    from shiftos.services.analysis.retrieval import retrieve_evidence
    from shiftos.services.analysis.validation import offline_result, validate_result

    def identity(name):
        return uuid5(NAMESPACE_URL, "https://example.invalid/shiftos/phase43/" + name)

    with database.session_factory() as session:
        original = session.get(DatasetVersion, UUID(version_id))
        observation = session.scalar(
            select(WorkforceObservation)
            .where(
                WorkforceObservation.version_id == original.id,
                WorkforceObservation.sector == "agriculture",
                WorkforceObservation.period_end <= datetime.now(UTC).date(),
            )
            .order_by(WorkforceObservation.period_end.desc(), WorkforceObservation.id)
        )
        if observation is None:
            return {"status": "NO_MATCHING_OBSERVATION", "model_requests": 0}
        reference = session.get(EvidenceReference, observation.evidence_id)
        source = session.get(Source, original.source_id)
        provenance = {
            "verification_copy": True,
            "original_is_synthetic": False,
            "original_version_id": str(original.id),
            "original_reference_id": str(reference.id),
            "original_observation_id": str(observation.id),
            "original_artifact_sha256": original.content_sha256,
            "attribution": "Source: Department of Statistics Malaysia / OpenDOSM, CC BY 4.0",
            "limitation": "Broad sector share, not occupation/skill demand or taught content",
        }
        session.add(
            Institution(
                id=identity("institution"),
                name="SYNTHETIC Brave Verification University",
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            Programme(
                id=identity("programme"),
                institution_id=identity("institution"),
                name="SYNTHETIC Bachelor of Agriculture",
                discipline_key="engineering",
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            ProgrammeRevision(
                id=identity("revision"),
                programme_id=identity("programme"),
                version_label="synthetic-brave-context-v1",
                is_synthetic=True,
            )
        )
        session.flush()
        session.get(Programme, identity("programme")).active_revision_id = identity("revision")
        session.add(
            Course(
                id=identity("course"),
                programme_revision_id=identity("revision"),
                course_name="SYNTHETIC Agriculture Statistics",
                year=1,
                is_synthetic=True,
            )
        )
        session.add(
            Source(
                id=identity("source"),
                publisher=source.publisher,
                title="SYNTHETIC verification copy: " + source.title,
                url=source.url,
                collected_at=original.retrieved_at,
                content_hash=original.content_sha256,
                evidence_class="synthetic_demo",
                license_status=source.license_status,
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            DatasetVersion(
                id=identity("version"),
                dataset_id=original.dataset_id,
                source_id=identity("source"),
                content_sha256=original.content_sha256,
                parser_version="phase43-verification-copy-1",
                context_sha256=hashlib.sha256(
                    json.dumps(provenance, sort_keys=True).encode()
                ).hexdigest(),
                retrieved_at=original.retrieved_at,
                publication_date=original.publication_date,
                artifact_url=original.artifact_url,
                metadata_json=provenance,
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            EvidenceReference(
                id=identity("reference"),
                version_id=identity("version"),
                locator=reference.locator,
                excerpt=reference.excerpt,
                review_status=reference.review_status,
                metadata_json=provenance,
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            WorkforceObservation(
                id=identity("observation"),
                version_id=identity("version"),
                evidence_id=identity("reference"),
                external_id=observation.external_id,
                sector=observation.sector,
                geography=observation.geography,
                period_start=observation.period_start,
                period_end=observation.period_end,
                indicator=observation.indicator,
                value=observation.value,
                unit=observation.unit,
                value_status=observation.value_status,
                limitations=observation.limitations,
                metadata_json={**observation.metadata_json, **provenance},
                is_synthetic=True,
            )
        )
        session.commit()
        permissions = json.loads(configuration().analysis_permissions_path.read_text())["sources"]
        packet = retrieve_evidence(
            session, identity("revision"), datetime.now(UTC), permitted_sources=permissions
        )
        matched = [item for item in packet.references if item.record_id == identity("observation")]
        assert len(matched) == 1 and matched[0].model_eligible
        result = validate_result(offline_result(packet).model_dump(mode="json"), packet)
        assert result.courses[0].workforce_alignment.citations
        assert result.courses[0].workforce_alignment.status == "insufficient_evidence"
        assert result.courses[0].needs_syllabus_confirmation
        return {
            "status": "RETRIEVED_AND_CITATION_VALIDATED",
            "model_requests": 0,
            "is_synthetic_association": True,
            "original_version_id": version_id,
            "observation_date": observation.period_end.isoformat(),
            "course_count": 1,
            "admitted_reference_count": len(matched),
            "title_only": True,
            "workforce_status": "insufficient_evidence",
        }


def live(budget):
    from alembic.config import Config
    from sqlalchemy import select

    from alembic import command
    from shiftos.db.session import create_database
    from shiftos.models import DatasetVersion
    from shiftos.services.analysis.providers import BraveSearch, ProviderError
    from shiftos.services.analysis.research import ResearchService

    if budget is None or not 0 < budget <= 0.05:
        raise ValueError("Fresh approval and at most $0.05 are required")
    ready = preflight()
    if ready["blockers"]:
        return ready
    receipt = CASE / "live-attempt.json"
    with receipt.open("x") as file:
        json.dump(
            {
                "status": "RESERVED",
                "approved_budget_usd": budget,
                "started_at": datetime.now(UTC).isoformat(),
            },
            file,
        )
    report = {
        "status": "FAILED",
        "search_request_count": 0,
        "claude_requests": 0,
        "gemini_requests": 0,
        "observed_cost": None,
    }
    database, search = None, None
    try:
        prepare()
        os.environ["DATABASE_URL"] = URL
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "alembic"))
        command.upgrade(config, "head")
        settings = configuration()
        scoped = json.loads(settings.analysis_research_policy.read_text())
        scoped.update(
            allowed_dataset_ids=[DATASET],
            queries_per_gap=1,
            max_documents=1,
            registry_path=str(ROOT / "data/dataset_registry.csv"),
            acquisition_policy_path=str(ROOT / "data/evidence_acquisition.json"),
            queries={"workforce": [QUERY]},
            search_result_storage_allowed=False,
        )
        path = CASE / "research-policy.json"
        write_json(path, scoped)
        settings = settings.model_copy(
            update={
                "research_enabled": True,
                "analysis_research_policy": path,
                "analysis_provider_max_attempts": 1,
                "analysis_provider_timeout_seconds": 20,
                "research_max_queries": 1,
                "research_timeout_seconds": 60,
                "analysis_external_processing_allowed": False,
                "claude_enabled": False,
                "gemini_enabled": False,
                "analysis_gemini_fallback_enabled": False,
            }
        )

        class SingleSearch(BraveSearch):
            def search(self, query):
                if self.request_attempts:
                    raise ProviderError("provider_deadline")
                return super().search(query)

        database = create_database(URL)
        search = SingleSearch(settings)
        research = ResearchService(database, settings, search_factory=lambda _: search)
        output = research.run("business", ["missing_workforce"])
        report.update(
            status="PARTIAL",
            research=output,
            search_request_count=search.request_attempts,
            search_metadata=search.last_response_metadata,
            approved_budget_usd=budget,
            finished_at=datetime.now(UTC).isoformat(),
        )
        assert search.request_attempts <= 1
        if output["version_ids"]:
            with database.session_factory() as session:
                versions = session.scalars(
                    select(DatasetVersion).where(
                        DatasetVersion.id.in_([UUID(value) for value in output["version_ids"]])
                    )
                ).all()
                assert all(
                    row.content_sha256 and row.artifact_url and row.retrieved_at and row.source_id
                    for row in versions
                )
                report["originals_persisted"] = len(versions)
            report["analysis_retrieval"] = check_analysis(database, output["version_ids"][0])
            if report["analysis_retrieval"]["status"] == "RETRIEVED_AND_CITATION_VALIDATED":
                report["status"] = "BRAVE_SOURCE_AND_RETRIEVAL_VERIFIED"
        return report
    finally:
        if search is not None:
            report["search_request_count"] = search.request_attempts
            report["search_metadata"] = search.last_response_metadata
        report["finished_at"] = datetime.now(UTC).isoformat()
        write_json(receipt, report)
        if database:
            database.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "live"])
    parser.add_argument("--approved-budget-usd", type=float)
    args = parser.parse_args()
    if args.action == "live" and (
        args.approved_budget_usd is None or not 0 < args.approved_budget_usd <= 0.05
    ):
        parser.error("Obtain explicit owner approval and a spending limit of at most $0.05")
    try:
        report = preflight() if args.action == "preflight" else live(args.approved_budget_usd)
        print(json.dumps(report, indent=2))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "detail": "Inspect the isolated report. No automatic retry.",
                }
            )
        )
        raise SystemExit(1) from None
