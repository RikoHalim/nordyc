"""Opt-in direct Gemini verification using the unchanged Claude comparison case.

Preflight is local only. Live verification permits one synthetic-course request,
with genuine attributed ESCO text, no repair/search/fallback or database access.
The existing academic schema and grounding validator remain authoritative.
"""

import re
import time

from shiftos.core.config import Settings
from shiftos.schemas.analysis import DIMENSIONS, ProgrammeResult
from shiftos.services.analysis.claude_verification import (
    VERIFICATION_MAX_OUTPUT_TOKENS,
    _esco_permissions,
    _sha256,
    _synthetic_packet,
)
from shiftos.services.analysis.providers import (
    MODEL_SYSTEM_INSTRUCTION,
    GeminiProvider,
    ProviderError,
)
from shiftos.services.analysis.validation import validate_result

PREFERRED_MODEL = "gemini-4-argon"
_TOKEN_FIELDS = {
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "thought_tokens",
    "total_tokens",
}


def _safe_model(value) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"gemini-[a-z0-9][a-z0-9.\-]{0,90}", value):
        return value
    return None


def inspect_gemini_configuration(settings: Settings) -> dict:
    """Inspect explicit settings/rights without requesting credentials or model lists."""
    credential = settings.gemini_api_key
    credential_present = bool(credential and credential.get_secret_value().strip())
    model = _safe_model(settings.gemini_model)
    permission_policy, permission_error = _esco_permissions(settings)
    blockers = [
        code
        for blocked, code in (
            (not settings.gemini_enabled, "gemini_disabled"),
            (not settings.analysis_external_processing_allowed, "external_processing_not_approved"),
            (not credential_present, "gemini_credential_missing"),
            (model is None, "gemini_model_missing_or_invalid"),
        )
        if blocked
    ]
    if permission_error:
        blockers.append(permission_error)
    return {
        "status": "blocked" if blockers else "configuration_ready",
        "provider": "gemini_direct",
        "preferred_model": PREFERRED_MODEL,
        "requested_model": model,
        "preferred_model_configured": model == PREFERRED_MODEL,
        "selected_for_analysis": settings.analysis_model_provider == "gemini",
        "gemini_enabled": settings.gemini_enabled,
        "external_processing_allowed": settings.analysis_external_processing_allowed,
        "credential_present": credential_present,
        "esco_processing_permitted": permission_error is None,
        "permission_policy": permission_policy,
        "availability": "not_verified",
        "provider_requests": 0,
        "blockers": blockers,
    }


def _metadata(provider) -> dict:
    value = getattr(provider, "last_response_metadata", None)
    metadata = value if isinstance(value, dict) else {}
    value = metadata.get("usage")
    usage = value if isinstance(value, dict) else {}
    count = getattr(provider, "request_attempts", None)
    if type(count) is not int or not 0 <= count <= 1:
        count = metadata.get("request_count")
    return {
        "actual_model": _safe_model(metadata.get("actual_model")),
        "usage": {
            key: value
            for key, value in usage.items()
            if key in _TOKEN_FIELDS and type(value) is int and 0 <= value <= 10**12
        },
        "provider_requests": count if type(count) is int and 0 <= count <= 1 else None,
        "observed_cost": None,
        "observed_cost_status": "not_reported",
    }


def verify_gemini(settings: Settings, *, provider_factory=GeminiProvider) -> dict:
    """One controlled attempt; errors retain safe usage, never raw upstream content."""
    preflight = inspect_gemini_configuration(settings)
    report = {
        "status": "blocked" if preflight["blockers"] else "failed",
        "preflight": preflight,
        "provider": "gemini_direct",
        "requested_model": preflight["requested_model"],
        "actual_model": None,
        "usage": {},
        "provider_requests": 0,
        "observed_cost": None,
        "observed_cost_status": "not_reported",
        "provider_latency_seconds": None,
        "is_synthetic": True,
        "course_count": 1,
        "citation_count": 0,
        "schema_validated": False,
        "grounding_validated": False,
        "insufficient_evidence_validated": False,
        "blockers": preflight["blockers"],
    }
    if preflight["blockers"]:
        return report
    bounded = settings.model_copy(
        update={
            "analysis_provider_max_attempts": 1,
            "gemini_max_output_tokens": min(
                settings.gemini_max_output_tokens, VERIFICATION_MAX_OUTPUT_TOKENS
            ),
            "analysis_gemini_fallback_enabled": False,
            "research_enabled": False,
        }
    )
    # Deliberately reuse the exact published Phase 4.1 packet, including its IDs.
    # No provider-specific evidence, easier grading or fabricated curriculum added.
    packet = _synthetic_packet(preflight["permission_policy"])
    packet_json = packet.model_dump(mode="json")
    schema = ProgrammeResult.model_json_schema()
    report.update(
        packet_sha256=_sha256(packet_json),
        schema_sha256=_sha256(schema),
        instruction_sha256=_sha256({"system": MODEL_SYSTEM_INSTRUCTION}),
        max_output_tokens=bounded.gemini_max_output_tokens,
        timeout_seconds=bounded.analysis_provider_timeout_seconds,
    )
    provider = None
    try:
        provider = provider_factory(bounded)
        started = time.monotonic()
        try:
            raw = provider.generate(packet_json, schema)
        finally:
            report["provider_latency_seconds"] = round(time.monotonic() - started, 6)
        report.update(_metadata(provider))
        ProgrammeResult.model_validate(raw)
        report["schema_validated"] = True
        result = validate_result(raw, packet)
        if result.result_mode != "live_model":
            report["error_code"] = "live_result_mode_required"
            return report
        report["grounding_validated"] = True
        report["insufficient_evidence_validated"] = all(
            getattr(course, dimension).status == "insufficient_evidence"
            for course in result.courses
            for dimension in DIMENSIONS
        )
        report["citation_count"] = sum(
            len(getattr(course, dimension).citations)
            for course in result.courses
            for dimension in DIMENSIONS
        )
        for failed, code in (
            (not report["citation_count"], "citation_check_not_exercised"),
            (not report["insufficient_evidence_validated"], "insufficiency_check_not_exercised"),
            (report["actual_model"] is None, "model_identity_unreported"),
            (report["provider_requests"] != 1, "single_request_not_confirmed"),
            (
                not {"input_tokens", "output_tokens"} <= report["usage"].keys(),
                "token_usage_unreported",
            ),
        ):
            if failed:
                report["error_code"] = code
                return report
        result_json = result.model_dump(mode="json")
        report.update(
            status="live_verified",
            availability="verified_by_request",
            preferred_model_used=report["actual_model"] == PREFERRED_MODEL,
            result_sha256=_sha256(result_json),
            evidence_packet=packet_json,
            result=result_json,
        )
    except ProviderError as exc:
        report["error_code"] = exc.code
    except (TypeError, ValueError, OverflowError, RecursionError):
        report["error_code"] = "analysis_validation_failed"
    except Exception:
        report["error_code"] = "gemini_verification_failed"
    if provider is not None:
        report.update(_metadata(provider))
    return report
