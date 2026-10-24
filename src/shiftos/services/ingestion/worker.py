"""Run queued catalogue jobs in a separate process; HTTP never fetches sources."""

import logging
import time
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import aliased

from shiftos.core.config import Settings
from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.db.session import Database
from shiftos.models import Institution, Job, Programme
from shiftos.repositories.catalogue import canonical_url, lock_institution, source_version
from shiftos.schemas.ingestion import (
    CatalogueImport,
    CatalogueResult,
    ProgrammeManifest,
    ProgrammeOutcome,
)
from shiftos.services.ingestion.catalogue import (
    check_origin,
    coverage,
    ensure_programme,
    import_programme,
)
from shiftos.services.ingestion.fetcher import FetchError, SafeFetcher
from shiftos.services.ingestion.parsers import CurriculumParseError, XmumCurriculumParser

logger = logging.getLogger("shiftos.catalogue")

# A new institution supplies a parser + reviewed origin configuration, not new tables.
PROVIDERS = {
    "xmum": {
        "name": "Xiamen University Malaysia",
        "website_url": "https://www.xmu.edu.my/",
        "directory_url": "https://www.xmu.edu.my/undergraduate-programmes",
        "allowed_hosts": ("www.xmu.edu.my", "xmu.edu.my"),
        "parser": XmumCurriculumParser,
    },
}


def queue_discovery(session, institution_id: UUID, provider: str, key: str | None):
    from shiftos.services.ingestion.catalogue import queue_job

    institution = lock_institution(session, institution_id)
    config = PROVIDERS[provider]
    if institution.is_synthetic or canonical_url(institution.website_url or "") != canonical_url(
        config["website_url"]
    ):
        raise DomainError(
            "CONFLICT", "Discovery provider does not match the institution's official website", 409
        )
    return queue_job(session, institution_id, "CURRICULUM_DISCOVERY", {"provider": provider}, key)


def provider_institution(session, provider: str) -> Institution:
    config = PROVIDERS[provider]
    matches = [
        i
        for i in session.scalars(select(Institution)).all()
        if i.website_url
        and not i.is_synthetic
        and canonical_url(i.website_url) == canonical_url(config["website_url"])
    ]
    if len(matches) > 1:
        raise DomainError(
            "CONFLICT", "Multiple institution identities match the provider; reconcile first", 409
        )
    if matches:
        return matches[0]
    institution = Institution(
        id=uuid5(NAMESPACE_URL, "shiftos:institution:provider:" + provider),
        name=config["name"],
        website_url=config["website_url"],
        is_synthetic=False,
    )
    session.add(institution)
    session.flush()
    return institution


def _summary(result: CatalogueResult) -> dict:
    result.imported_programmes = sum(e.status in {"imported", "historical"} for e in result.entries)
    result.unchanged_programmes = sum(e.status == "unchanged" for e in result.entries)
    result.failed_programmes = sum(e.status == "failed" for e in result.entries)
    result.course_count = sum(e.course_count for e in result.entries)
    result.verified_title_count = sum(e.verified_title_count for e in result.entries)
    return CatalogueResult.model_validate(result.model_dump()).model_dump(mode="json")


def lock_running_job(session, job_id: UUID) -> Job:
    """Fence stale workers against operator recovery in the same write transaction."""
    job = session.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None or job.status != JobStatus.RUNNING:
        raise DomainError("CONFLICT", "Catalogue job is no longer running", 409)
    return job


def _save_progress(database: Database, job_id: UUID, result: CatalogueResult) -> None:
    with database.session_factory() as session:
        job = lock_running_job(session, job_id)
        job.result_json = _summary(result)
        session.commit()


def _manual(database: Database, job: Job) -> CatalogueResult:
    payload = dict(job.payload_json)
    target = UUID(payload.pop("target_id")) if payload.get("target_id") else None
    data = CatalogueImport.model_validate(payload)
    result = CatalogueResult(
        provider="structured_manual", discovered_programmes=len(data.programmes)
    )
    for manifest in data.programmes:
        with database.session_factory() as session:
            try:
                lock_running_job(session, job.id)
                outcome = import_programme(
                    session,
                    job.institution_id,
                    manifest,
                    synthetic=data.is_synthetic,
                    parser_version="structured-json-1",
                    acquisition_mode="reviewed_manual" if manifest.reviewed else "manual_candidate",
                    target_id=target,
                )
                stats = coverage(
                    session, UUID(outcome["programme_id"]), UUID(outcome["revision_id"])
                )
                result.entries.append(
                    ProgrammeOutcome(
                        **outcome,
                        source_url=str(manifest.source_url),
                        verified_title_count=stats.verified_title_count,
                    )
                )
            except DomainError as exc:
                session.rollback()
                result.entries.append(
                    ProgrammeOutcome(
                        name=manifest.name,
                        source_url=str(manifest.source_url),
                        status="failed",
                        error_code=exc.code,
                        message=exc.message,
                    )
                )
        _save_progress(database, job.id, result)
    return result


def _discover(database: Database, job: Job, settings: Settings, fetcher_factory) -> CatalogueResult:
    config = PROVIDERS[job.payload_json["provider"]]
    parser = config["parser"]()
    result = CatalogueResult(
        provider=job.payload_json["provider"], directory_url=config["directory_url"]
    )
    deadline = time.monotonic() + 600
    with fetcher_factory(
        config["allowed_hosts"],
        enabled=settings.discovery_enabled,
        terms_reviewed=settings.discovery_terms_reviewed,
    ) as fetcher:
        directory = fetcher.fetch_html(config["directory_url"])
        links = parser.parse_directory(directory.html, directory.url)
        if len(links) > 100:
            raise DomainError(
                "DISCOVERY_LIMIT",
                "Directory exceeds the 100-programme review bound; use manual import",
                422,
            )
        result.discovered_programmes = len(links)
        result.directory_retrieved_at = directory.retrieved_at
        with database.session_factory() as session:
            lock_running_job(session, job.id)
            institution = lock_institution(session, job.institution_id)
            source = source_version(
                session,
                publisher=config["name"],
                title="XMUM undergraduate programme directory",
                url=directory.url,
                content_hash=directory.sha256,
                retrieved_at=directory.retrieved_at,
                synthetic=False,
                reviewed=True,
                license_status="public_facts_only_rights_unconfirmed",
            )
            institution.source_id, institution.source_locator = source.id, "programme directory"
            known = session.scalars(
                select(Programme).where(Programme.institution_id == institution.id)
            ).all()
            found = {canonical_url(item.canonical_url) for item in links}
            result.missing_from_directory = [
                p.id
                for p in known
                if p.ingestion_key
                and p.canonical_url
                and canonical_url(p.canonical_url) not in found
            ]
            targets = []
            for link in links:
                check_origin(institution, link.canonical_url)
                programme = ensure_programme(session, institution, link.name, link.canonical_url)
                if programme.source_id is None:
                    programme.source_id, programme.source_locator = source.id, link.source_locator
                targets.append((link, programme.id))
            session.commit()
        # Directory success only establishes discovered programme records, not course coverage.
        result.entries = [
            ProgrammeOutcome(
                programme_id=pid, name=link.name, source_url=link.canonical_url, status="discovered"
            )
            for link, pid in targets
        ]
        _save_progress(database, job.id, result)
        for index, (link, pid) in enumerate(targets):
            try:
                if time.monotonic() > deadline:
                    raise DomainError(
                        "DISCOVERY_LIMIT",
                        "Discovery time budget reached; remaining programmes need manual import",
                        422,
                    )
                # Both are official aliases; use the reachable configured host, retain final URL.
                url = link.canonical_url.replace("https://xmu.edu.my/", "https://www.xmu.edu.my/")
                page = fetcher.fetch_html(url)
                parsed = parser.parse_programme(page.html, page.url)
                manifest = ProgrammeManifest(
                    name=link.name,
                    canonical_url=link.canonical_url,
                    source_url=page.url,
                    source_locator="Main Courses",
                    retrieved_at=page.retrieved_at,
                    content_hash=page.sha256,
                    reviewed=True,
                    license_status="public_facts_only_rights_unconfirmed",
                    notes=parsed.notes,
                    courses=[c.model_dump() for c in parsed.courses],
                )
                with database.session_factory() as session:
                    lock_running_job(session, job.id)
                    outcome = import_programme(
                        session,
                        job.institution_id,
                        manifest,
                        synthetic=False,
                        parser_version=parser.version,
                        acquisition_mode="official_html",
                        target_id=pid,
                    )
                    stats = coverage(session, pid, UUID(outcome["revision_id"]))
                result.entries[index] = ProgrammeOutcome(
                    **outcome, source_url=page.url, verified_title_count=stats.verified_title_count
                )
            except (FetchError, CurriculumParseError, DomainError, ValidationError) as exc:
                result.entries[index] = ProgrammeOutcome(
                    programme_id=pid,
                    name=link.name,
                    source_url=link.canonical_url,
                    status="failed",
                    error_code=getattr(exc, "code", "EXTRACTION_VALIDATION_ERROR"),
                    message="Source could not be safely imported; use reviewed structured JSON. "
                    "Existing curriculum retained.",
                )
            _save_progress(database, job.id, result)
    return result


def run_once(database: Database, settings: Settings, *, fetcher_factory=SafeFetcher) -> UUID | None:
    """Claim once, commit status, do slow work outside request/claim transactions."""
    with database.session_factory() as session:
        other = aliased(Job)
        institution_busy = (
            select(other.id)
            .where(other.institution_id == Job.institution_id, other.status == JobStatus.RUNNING)
            .exists()
        )
        job = session.scalar(
            select(Job)
            .where(
                Job.kind.in_(
                    [
                        "CURRICULUM_IMPORT",
                        "CURRICULUM_DISCOVERY",
                        "CURRICULUM_PDF_UPLOAD",
                        "PROGRAMME_ANALYSIS",
                        "CAREER_ANALYSIS",
                    ]
                ),
                Job.status == JobStatus.QUEUED,
                ~institution_busy,
            )
            .order_by(Job.created_at, Job.id)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return None
        lock_institution(session, job.institution_id)
        running = session.scalar(
            select(Job.id).where(
                Job.institution_id == job.institution_id, Job.status == JobStatus.RUNNING
            )
        )
        if running:
            return None
        job.status, job.started_at = JobStatus.RUNNING, datetime.now(UTC)
        session.commit()
        session.expunge(job)
    try:
        if job.kind == "CAREER_ANALYSIS":
            from shiftos.services.career.orchestrator import process_career_job

            process_career_job(database, job, settings)
            return job.id
        if job.kind == "PROGRAMME_ANALYSIS":
            from shiftos.services.analysis.orchestrator import process_analysis_job

            process_analysis_job(database, job, settings)
            return job.id
        if job.kind == "CURRICULUM_PDF_UPLOAD":
            from shiftos.services.ingestion.uploads import process_pdf_upload

            result = process_pdf_upload(database, job, settings)
        else:
            result = (
                _manual(database, job)
                if job.kind == "CURRICULUM_IMPORT"
                else _discover(database, job, settings, fetcher_factory)
            )
        status = JobStatus.PARTIAL if result.failed_programmes else JobStatus.SUCCEEDED
        if result.entries and all(e.status == "failed" for e in result.entries):
            status = JobStatus.FAILED
        error = (
            "Some programme pages failed; use structured manual import"
            if result.failed_programmes
            else None
        )
        output = _summary(result)
    except (FetchError, CurriculumParseError, DomainError, ValidationError) as exc:
        status, output = JobStatus.FAILED, None
        error = getattr(exc, "code", "INVALID_MANIFEST") + (
            ": Career analysis failed; review frozen inventory, evidence and source permissions"
            if job.kind == "CAREER_ANALYSIS"
            else ": Catalogue acquisition failed; use reviewed structured JSON"
        )
    except Exception:
        # Previously persisted per-programme progress is retained, with a visible terminal failure.
        status, output, error = (
            JobStatus.FAILED,
            None,
            "WORKER_ERROR: Career analysis failed; inspect server diagnostics"
            if job.kind == "CAREER_ANALYSIS"
            else "WORKER_ERROR: Catalogue job failed; inspect server diagnostics",
        )
        logger.error("catalogue_worker_failed job_id=%s", job.id)
    with database.session_factory() as session:
        stored = session.scalar(select(Job).where(Job.id == job.id).with_for_update())
        if stored is not None and stored.status == JobStatus.RUNNING:
            stored.status, stored.completed_at, stored.error = status, datetime.now(UTC), error
            if output is not None:
                stored.result_json = output
            session.commit()
    return job.id


def fail_stale_jobs(database: Database) -> int:
    """Explicit operator recovery after a crash; never silently rerun partial work."""
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    with database.session_factory() as session:
        jobs = session.scalars(
            select(Job)
            .where(
                Job.kind.in_(
                    [
                        "CURRICULUM_IMPORT",
                        "CURRICULUM_DISCOVERY",
                        "CURRICULUM_PDF_UPLOAD",
                        "PROGRAMME_ANALYSIS",
                        "CAREER_ANALYSIS",
                    ]
                ),
                Job.status == JobStatus.RUNNING,
                Job.started_at < cutoff,
            )
            .with_for_update(skip_locked=True)
        ).all()
        for job in jobs:
            job.status, job.completed_at, job.error = (
                JobStatus.FAILED,
                datetime.now(UTC),
                "STALE_WORKER: Requeue explicitly; completed programme imports are safe to replay",
            )
        session.commit()
        return len(jobs)
