"""Explicit administrative acquisition/import. Never runs at application startup."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from shiftos.db.base import utc_now
from shiftos.models.evidence import Dataset, EvidenceIngestionJob, EvidenceProcessingLog
from shiftos.repositories.evidence import EvidenceLoadError, load_batch, sync_registry
from shiftos.services.evidence.acquisition import Artifact, DatasetFetcher
from shiftos.services.evidence.parsers import parse_dataset
from shiftos.services.evidence.registry import read_registry
from shiftos.services.ingestion.fetcher import FetchError

PARSER_VERSION = "evidence-1.0"
MAX_BYTES = 5_000_000


class AcquisitionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    adapter: str
    format: Literal["csv", "xlsx", "json", "pdf"]
    url: str | None = None
    access_reviewed: bool = False
    reuse_reviewed: bool = False
    retain_raw: bool = False
    absent_robots_policy: Literal["deny", "allow"] = "deny"
    instructions: str = Field(min_length=1)


def run_ingestion(
    database,
    *,
    registry_path=Path("data/dataset_registry.csv"),
    policy_path=Path("data/evidence_acquisition.json"),
    dataset_ids=None,
    local_path=None,
    retrieved_at=None,
    enabled=False,
    is_synthetic=False,
    storage_path=Path("data/raw/evidence"),
    fetcher_factory=DatasetFetcher,
):
    entries = read_registry(registry_path)
    raw_rules = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    rules = {key: AcquisitionRule.model_validate(value) for key, value in raw_rules.items()}
    selected = set(dataset_ids or [entry.id for entry in entries])
    if selected - {entry.id for entry in entries}:
        raise ValueError("Unknown dataset ID")
    if local_path and (len(selected) != 1 or retrieved_at is None):
        raise ValueError("Local imports require one dataset and original retrieval timestamp")
    if retrieved_at is not None and (retrieved_at.tzinfo is None or retrieved_at > utc_now()):
        raise ValueError("Retrieval timestamp must be timezone-aware and not in the future")
    with database.session_factory() as session:
        sync_registry(session, entries)
        session.commit()
    reports = []
    for entry in entries:
        if entry.id not in selected:
            continue
        with database.session_factory() as session:
            dataset = session.scalar(select(Dataset).where(Dataset.registry_key == entry.id))
            job = EvidenceIngestionJob(
                dataset_id=dataset.id,
                status="RUNNING",
                started_at=utc_now(),
                is_synthetic=is_synthetic,
            )
            session.add(job)
            session.commit()
            job_id, dataset_id = job.id, dataset.id
        rule = rules.get(entry.id)
        report = {
            "dataset": entry.id,
            "access_method": "manual" if local_path else "automatic",
            "status": "FAILED",
            "records_imported": 0,
            "source_date": entry.latest_verified_publication_date,
            "errors": [],
            "job_id": str(job_id),
            "is_synthetic": is_synthetic,
        }
        status = "FAILED"
        error = None
        try:
            if rule is None:
                status = "SKIPPED" if entry.category == "A" else "MANUAL_REQUIRED"
                raise FetchError(
                    "no_adapter",
                    "No approved adapter: review source/rights, obtain a permitted file "
                    "and configure a source-specific import rule.",
                )
            if not rule.reuse_reviewed:
                status = "MANUAL_REQUIRED"
                raise FetchError("reuse_review_required", rule.instructions)
            if entry.verification_status == "Unverified" and not is_synthetic:
                status = "MANUAL_REQUIRED"
                raise FetchError(
                    "source_unverified", "Verify the official source before importing evidence."
                )
            endpoint = rule.url or entry.download_api_url
            # Alternate endpoints must be deliberately recorded in the registry, not guessed.
            if not endpoint or endpoint not in {entry.download_api_url, entry.source_url}:
                raise ValueError("Acquisition URL must match a registered endpoint")
            if local_path:
                path = Path(local_path)
                if not 0 < path.stat().st_size <= MAX_BYTES:
                    raise ValueError("Invalid artifact size")
                content = path.read_bytes()
                artifact = Artifact(
                    endpoint, content, hashlib.sha256(content).hexdigest(), retrieved_at
                )
            else:
                if not enabled or not rule.access_reviewed:
                    status = "MANUAL_REQUIRED"
                    raise FetchError("live_fetch_disabled", rule.instructions)
                from urllib.parse import urlsplit

                with fetcher_factory(
                    {urlsplit(endpoint).hostname},
                    enabled=True,
                    terms_reviewed=True,
                    max_bytes=MAX_BYTES,
                    absent_robots_policy=rule.absent_robots_policy,
                ) as fetcher:
                    artifact = fetcher.fetch(endpoint)
            batch = parse_dataset(
                artifact.content, format=rule.format, adapter=rule.adapter, dataset=entry
            )
            if not batch.records:
                raise ValueError("No records extracted; check format/layout")
            context = {
                "adapter": rule.adapter,
                "format": rule.format,
                "publication_date": entry.latest_verified_publication_date,
                "endpoint": endpoint,
                "is_synthetic": is_synthetic,
                "licence": entry.licence,
                "rights_status": entry.rights_status,
            }
            if rule.retain_raw:
                directory = Path(storage_path) / entry.id
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / f"{artifact.sha256}.{rule.format}"
                if not path.exists():
                    path.write_bytes(artifact.content)
                elif hashlib.sha256(path.read_bytes()).hexdigest() != artifact.sha256:
                    raise ValueError("Stored artifact checksum mismatch")
            with database.session_factory() as session:
                dataset = session.get(Dataset, dataset_id)
                version, created, counts = load_batch(
                    session,
                    dataset,
                    entry,
                    artifact,
                    batch,
                    parser_version=PARSER_VERSION,
                    context=context,
                    is_synthetic=is_synthetic,
                )
                job = session.get(EvidenceIngestionJob, job_id)
                status = "SUCCEEDED" if created else "UNCHANGED"
                report.update(
                    status=status,
                    counts=counts,
                    records_imported=sum(counts.values()) if created else 0,
                    version_id=str(version.id),
                    warnings=batch.warnings,
                    sha256=artifact.sha256,
                    retrieved_at=artifact.retrieved_at.isoformat(),
                )
                job.version_id = version.id
                job.records_imported = report["records_imported"]
                session.commit()
        except FetchError as exc:
            error = exc.code
            report["errors"].append({"code": exc.code, "message": exc.message})
        except EvidenceLoadError as exc:
            status = "FAILED"
            error = exc.code
            report["errors"].append(
                {"code": exc.code, "message": exc.message, "locator": exc.locator}
            )
        except Exception as exc:
            status = "FAILED"
            report["records_imported"] = 0
            for key in ("version_id", "counts"):
                report.pop(key, None)
            # Never persist upstream responses, credentials, raw content or SQL parameters.
            error = "import_rejected"
            report["errors"].append(
                {
                    "code": error,
                    "message": "Artifact, schema, classification or database validation failed.",
                    "exception_type": type(exc).__name__,
                }
            )
        report["status"] = status
        with database.session_factory() as session:
            job = session.get(EvidenceIngestionJob, job_id)
            job.status, job.completed_at, job.error, job.result_json = (
                status,
                utc_now(),
                error,
                report,
            )
            session.add(
                EvidenceProcessingLog(
                    job_id=job_id,
                    level="ERROR" if error else "INFO",
                    code=error or status,
                    locator=report["errors"][0].get("locator") if error else None,
                    message=report["errors"][0]["message"]
                    if error
                    else "Immutable dataset version loaded or reused.",
                    is_synthetic=is_synthetic,
                )
            )
            session.commit()
        reports.append(report)
    return reports
