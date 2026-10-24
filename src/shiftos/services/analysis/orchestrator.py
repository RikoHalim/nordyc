"""Execute bounded screening jobs outside HTTP; freeze source and result lineage."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select

from shiftos.core.enums import JobStatus
from shiftos.core.errors import DomainError
from shiftos.models import Job
from shiftos.repositories.analysis import (
    inventory_snapshot,
    lock_analysis_for_job,
    replace_findings,
)
from shiftos.repositories.catalogue import digest
from shiftos.schemas.analysis import AnalysisRequest, EvidencePacket, ProgrammeResult
from shiftos.services.analysis.providers import GeminiProvider, ProviderError
from shiftos.services.analysis.research import ResearchService
from shiftos.services.analysis.retrieval import retrieve_evidence
from shiftos.services.analysis.validation import assemble_result, offline_result, validate_result

logger = logging.getLogger("shiftos.analysis")
PROMPT_VERSION = "phase4-grounded-1"
BATCH_SIZE = 20
MAX_MODEL_BATCHES = 10
MAX_RUN_SECONDS = 600


def _permissions(settings) -> tuple[dict, dict]:
    path = settings.analysis_permissions_path
    try:
        if path.stat().st_size > 100_000:
            raise ValueError
        policy = json.loads(path.read_text(encoding="utf-8"))
        sources = policy["sources"]
        if not isinstance(sources, dict) or not policy.get("version"):
            raise ValueError
        for key, rule in sources.items():
            if not isinstance(key, str) or not isinstance(rule, dict):
                raise ValueError
            if not isinstance(rule.get("basis"), str) or not rule["basis"].strip():
                raise ValueError
            for flag in (
                "internal_analysis_allowed",
                "external_model_allowed",
                "excerpt_output_allowed",
            ):
                if type(rule.get(flag)) is not bool:
                    raise ValueError
        return sources, {"version": policy["version"], "sha256": digest(policy)}
    except (OSError, ValueError, KeyError, TypeError):
        raise DomainError(
            "ANALYSIS_POLICY_INVALID", "Configure a valid explicit analysis-use policy", 503
        ) from None


def _retrieve(database, revision_id, cutoff, permissions) -> EvidencePacket:
    with database.session_factory() as session:
        return retrieve_evidence(session, revision_id, cutoff, permitted_sources=permissions)


def _batch_packet(packet: EvidencePacket, courses) -> EvidencePacket:
    reference_ids = {rid for course in courses for rid in course.reference_ids}
    permitted_ids = {
        item.id for item in packet.references if item.id in reference_ids and item.model_eligible
    }
    batch = packet.model_copy(
        deep=True,
        update={
            "courses": courses,
            "references": [item for item in packet.references if item.id in reference_ids],
            "radar": [
                item
                for item in packet.radar
                if item.get("before_reference_id") in permitted_ids
                and item.get("after_reference_id") in permitted_ids
            ],
            "manifest_hash": "",
        },
    )
    batch.manifest_hash = digest(batch.model_dump(mode="json", exclude={"manifest_hash"}))
    return batch


def _analyse(packet, settings, provider_factory, deadline):
    # The deterministic fallback does not impersonate a live model or invent evidence.
    fallback = offline_result(packet)
    if not packet.courses:
        return fallback, {"status": "empty_inventory", "calls": 0, "fallback_courses": 0}
    provider = provider_factory(settings)
    provider.deadline = deadline
    findings, errors, calls = [], [], 0
    aborted = False
    model_courses = 0
    for offset in range(0, len(packet.courses), BATCH_SIZE):
        courses = packet.courses[offset : offset + BATCH_SIZE]
        batch = _batch_packet(packet, courses)
        if aborted or offset // BATCH_SIZE >= MAX_MODEL_BATCHES or time.monotonic() >= deadline:
            errors.append("model_course_budget_exhausted" if not aborted else "model_unavailable")
            findings.extend(offline_result(batch).courses)
            continue
        accepted = None
        for repair in range(2):
            try:
                body = batch.model_dump(mode="json")
                if repair:
                    body["validation_feedback"] = (
                        "The previous result violated the supplied schema or evidence rules. "
                        "Return every course exactly once with supported citations "
                        "or insufficiency."
                    )
                calls += 1
                raw = provider.generate(body, ProgrammeResult.model_json_schema())
                accepted = validate_result(raw, batch)
                if accepted.result_mode != "live_model":
                    raise ValueError("Live provider must disclose live_model output")
                break
            except ProviderError as exc:
                errors.append(exc.code)
                aborted = True
                break
            except (ValidationError, ValueError, TypeError, KeyError):
                errors.append("model_output_not_grounded")
        if accepted is None:
            findings.extend(offline_result(batch).courses)
        else:
            findings.extend(accepted.courses)
            model_courses += len(accepted.courses)
    # Programme totals are application-derived, never model-generated statistics.
    result = assemble_result(
        packet,
        findings,
        "live_model" if model_courses else fallback.result_mode,
    )
    result = validate_result(result.model_dump(mode="json"), packet)
    return result, {
        "status": "verified_output" if not errors else "partial_or_unavailable",
        "calls": calls,
        "validated_model_courses": model_courses,
        "fallback_courses": len(findings) - model_courses,
        "reasons": sorted(set(errors)),
    }


def process_analysis_job(
    database,
    job: Job,
    settings,
    *,
    provider_factory=GeminiProvider,
    research_factory=ResearchService,
) -> None:
    """Fence and atomically publish all findings, manifest and terminal job status."""
    deadline = time.monotonic() + MAX_RUN_SECONDS
    try:
        permissions, permission_policy = _permissions(settings)
        with database.session_factory() as session:
            run = lock_analysis_for_job(session, job.id)
            request = AnalysisRequest.model_validate(run.request_json)
            original_manifest = dict(run.manifest_json)
            inventory = inventory_snapshot(session, run.programme_revision_id)
            if digest(inventory) != original_manifest.get("inventory_hash"):
                raise DomainError(
                    "CURRICULUM_CHANGED",
                    "Course inventory changed after submission; queue a new run",
                    409,
                )
            if len(inventory) > settings.analysis_max_courses:
                raise DomainError(
                    "ANALYSIS_LIMIT", "Course inventory exceeds the configured bound", 422
                )
            revision_id = run.programme_revision_id
            mode = run.mode
        packet = _retrieve(database, revision_id, request.as_of or datetime.now(UTC), permissions)
        research = {"status": "not_required", "attempts": [], "version_ids": [], "outcomes": []}
        if packet.gaps:
            if mode == "offline":
                research["status"] = "offline_disabled"
            elif request.as_of is not None:
                research["status"] = "historical_cutoff_no_refresh"
            elif not request.research:
                research["status"] = "request_disabled"
            else:
                try:
                    research = research_factory(database, settings).run(
                        packet.discipline, packet.gaps, is_synthetic=packet.is_synthetic
                    )
                except Exception:
                    # Upstream bodies/errors never become evidence or diagnostic text.
                    research = {
                        **research,
                        "status": "research_failed",
                        "outcomes": ["sanitized_failure"],
                    }
                if research.get("version_ids"):
                    packet = _retrieve(database, revision_id, datetime.now(UTC), permissions)
        if mode == "offline":
            result = offline_result(packet)
            model = {
                "status": "offline_not_called",
                "calls": 0,
                "fallback_courses": len(packet.courses),
            }
        else:
            result, model = _analyse(packet, settings, provider_factory, deadline)
        result = validate_result(result.model_dump(mode="json"), packet)
        if _permissions(settings)[1] != permission_policy:
            raise DomainError(
                "ANALYSIS_POLICY_CHANGED", "Analysis-use policy changed; queue a new run", 409
            )
        manifest = {
            **original_manifest,
            "packet": packet.model_dump(mode="json"),
            "source_policy_hash": packet.source_policy_hash,
            "permission_policy": permission_policy,
            "rules_version": packet.policy_version,
            "model_provider": "gemini_direct",
            "model_configured": settings.gemini_model or None,
            "prompt_version": PROMPT_VERSION,
            "schema_version": result.schema_version,
            "model_processing": model,
        }
        fingerprint = digest(
            {
                "packet_hash": packet.manifest_hash,
                "permission_policy": permission_policy,
                "request": request.model_dump(mode="json"),
                "model": settings.gemini_model or None,
                "prompt": PROMPT_VERSION,
                "schema": result.schema_version,
                "model_processing": model,
            }
        )
        with database.session_factory() as session:
            run = lock_analysis_for_job(session, job.id)
            if (
                digest(inventory_snapshot(session, revision_id))
                != original_manifest["inventory_hash"]
            ):
                raise DomainError(
                    "CURRICULUM_CHANGED", "Course inventory changed during analysis", 409
                )
            replace_findings(session, run, [row.model_dump(mode="json") for row in result.courses])
            run.manifest_json, run.research_json = manifest, research
            run.summary_json = result.model_dump(mode="json", exclude={"courses"})
            run.fingerprint = fingerprint
            run.model_name = (settings.gemini_model or None) if model.get("calls", 0) else None
            run.prompt_version, run.schema_version = PROMPT_VERSION, result.schema_version
            stored = session.get(Job, job.id)
            stored.result_json = {
                "analysis_id": str(run.id),
                "summary": result.summary.model_dump(),
                "result_mode": result.result_mode,
                "model_processing": model,
                "research_status": research.get("status"),
                "fingerprint": fingerprint,
            }
            stored.status = (
                JobStatus.PARTIAL
                if mode == "live" and model["status"] != "verified_output"
                else JobStatus.SUCCEEDED
            )
            stored.completed_at = datetime.now(UTC)
            stored.error = None
            session.commit()
    except Exception as exc:
        code = exc.code if isinstance(exc, DomainError) else "ANALYSIS_PROCESSING_FAILED"
        logger.error("analysis_job_failed job_id=%s code=%s", job.id, code)
        with database.session_factory() as session:
            stored = session.scalar(select(Job).where(Job.id == job.id).with_for_update())
            if stored is not None and stored.status == JobStatus.RUNNING:
                stored.status, stored.completed_at = JobStatus.FAILED, datetime.now(UTC)
                stored.error = code + ": Analysis could not be completed; inspect the frozen run"
                session.commit()
