"""Explicit managed-Claude verification: a fictional course, one genuine source.

Configuration inspection performs no provider construction or requests. The live
helper is called only by an explicit administrative action; it does not discover
credentials or fall back to another model. A successful check verifies transport,
the real analysis schema and grounding for one synthetic course, not academic
accuracy, Replit environment identity or a billing amount.
"""

import hashlib
import json
import re
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from shiftos.core.config import Settings, normalize_replit_anthropic_base_url
from shiftos.schemas.analysis import (
    DIMENSIONS,
    CourseEvidence,
    EvidenceItem,
    EvidencePacket,
    ProgrammeResult,
    RightsDecision,
)
from shiftos.services.analysis.providers import ClaudeProvider, ProviderError
from shiftos.services.analysis.validation import validate_result

PREFERRED_MODEL = "claude-opus-5"
VERIFICATION_MAX_OUTPUT_TOKENS = 4096
# Exact attributed English source text/provenance from the committed reviewed pack.
# The runtime does not depend on the repository's current working directory.
_ESCO_URI = "http://data.europa.eu/esco/skill/700ea222-8139-4c48-95cf-014855565530"
_ESCO_DESCRIPTION_NODE = (
    "http://data.europa.eu/esco/node-literal/d4e0a967-cd2e-457d-8e12-2a68fd8e03b7"
)
_ESCO_LABEL = "irrigation systems"
_ESCO_DESCRIPTION = "The methods and systems management in irrigation."
_ESCO_RETRIEVED_AT = "2026-10-23T19:57:05.013428+00:00"
_ESCO_TTL_URL = (
    "https://ec.europa.eu/esco/download/"
    "ESCO%20dataset%20-%20v1.0.3%20-%20classification%20-%20%20-%20ttl.zip"
)
_ESCO_TTL_SHA256 = "86f7082991054352c1c0cb7b97711e68967fd54b536a3aa7cb9ed5b68ec9c8b9"
_ESCO_DESCRIPTION_SHA256 = "f3c28b0e6306517ffe3e370509a4243e10348e403b5e9b285d42cb7d240b3726"
_ESCO_ATTRIBUTION = "This service uses the ESCO classification of the European Commission."
_ESCO_PACK = "data/reference_packs/esco-v1.0.3.subset.reviewed.json"
_TOKEN_FIELDS = {
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
}


def _safe_model(value) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"claude-[a-z0-9][a-z0-9.\-]{0,90}", value):
        return value
    return None


def _sha256(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _esco_permissions(settings: Settings) -> tuple[dict | None, str | None]:
    """Fail closed unless the configured bounded policy admits this exact source."""
    try:
        with settings.analysis_permissions_path.open("rb") as stream:
            raw = stream.read(100_001)
        if len(raw) > 100_000:
            return None, "esco_permissions_invalid"
        policy = json.loads(raw.decode("utf-8"))
        if not isinstance(policy, dict):
            return None, "esco_permissions_invalid"
        version = policy.get("version")
        if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", version):
            return None, "esco_permissions_invalid"
        sources = policy.get("sources")
        if not isinstance(sources, dict):
            return None, "esco_permissions_invalid"
        rule = sources.get("C-ESCO-V103")
        if not isinstance(rule, dict):
            return None, "esco_processing_not_permitted"
        flags = ("internal_analysis_allowed", "external_model_allowed", "excerpt_output_allowed")
        if not all(rule.get(flag) is True for flag in flags):
            return None, "esco_processing_not_permitted"
        if not isinstance(rule.get("basis"), str) or not rule["basis"].strip():
            return None, "esco_permissions_invalid"
        return {"version": version, "sha256": _sha256(policy)}, None
    except OSError:
        return None, "esco_permissions_unavailable"
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None, "esco_permissions_invalid"


def inspect_claude_configuration(settings: Settings) -> dict:
    """Return secret-safe readiness; sufficient configuration is not availability."""
    key = settings.replit_anthropic_api_key
    credential_present = bool(key and key.get_secret_value().strip())
    base_present = bool(settings.replit_anthropic_base_url)
    base_valid = False
    if base_present:
        try:
            normalize_replit_anthropic_base_url(settings.replit_anthropic_base_url)
            base_valid = True
        except (TypeError, ValueError):
            pass
    model = _safe_model(settings.claude_model)
    permission_policy, permission_error = _esco_permissions(settings)
    blockers = []
    for condition, code in (
        (not settings.claude_enabled, "claude_disabled"),
        (not settings.analysis_external_processing_allowed, "external_processing_not_approved"),
        (not credential_present, "managed_credential_missing"),
        (not base_present, "managed_base_url_missing"),
        (base_present and not base_valid, "managed_base_url_invalid"),
        (model is None, "claude_model_invalid"),
    ):
        if condition:
            blockers.append(code)
    if permission_error:
        blockers.append(permission_error)
    return {
        "status": "blocked" if blockers else "configuration_ready",
        "provider": "replit_claude",
        "preferred_model": PREFERRED_MODEL,
        "requested_model": model,
        "preferred_model_configured": model == PREFERRED_MODEL,
        "selected_for_analysis": settings.analysis_model_provider == "replit_claude",
        "claude_enabled": settings.claude_enabled,
        "external_processing_allowed": settings.analysis_external_processing_allowed,
        "managed_credential_present": credential_present,
        "managed_base_url_present": base_present,
        "managed_base_url_valid": base_valid,
        "esco_processing_permitted": permission_error is None,
        "permission_policy": permission_policy,
        "availability": "not_verified",
        "provider_requests": 0,
        "blockers": blockers,
    }


def _synthetic_packet(permission_policy: dict) -> EvidencePacket:
    """Copy one real, permitted ESCO skill into a labelled fictional-course lane.

    The synthetic flag describes this verification copy/association, never the
    origin of the quoted public text. Original source identifiers are explicit.
    """

    def identity(name):
        return uuid5(NAMESPACE_URL, f"https://example.invalid/shiftos/claude-verification/{name}")

    reference_id = UUID(_ESCO_URI.rsplit("/", 1)[1])
    reference = EvidenceItem(
        id=f"skill:{reference_id}",
        kind="skill",
        record_id=reference_id,
        version_id=identity("version"),
        evidence_reference_id=identity("reference"),
        source_id=identity("source"),
        dataset_key="C-ESCO-V103",
        evidence_class="synthetic_demo",
        scope="occupation_benchmark",
        source_url=_ESCO_URI,
        publisher="European Commission DG EMPL",
        title="ESCO v1.0.3: irrigation systems (synthetic verification copy)",
        locator=(
            f"partial TTL subject <{_ESCO_URI}>/skos:prefLabel; "
            f"description node <{_ESCO_DESCRIPTION_NODE}>/esco:nodeLiteral[@en]"
        ),
        excerpt=f"{_ESCO_LABEL}: {_ESCO_DESCRIPTION}",
        publication_date=None,
        date_precision="unknown",
        retrieved_at=datetime.fromisoformat(_ESCO_RETRIEVED_AT),
        review_status="reviewed",
        is_synthetic=True,
        rights=RightsDecision(
            internal_analysis_allowed=True,
            external_model_allowed=True,
            excerpt_output_allowed=True,
            basis=(
                "European Commission ESCO reuse acknowledgement/adaptation terms and explicit "
                "configured C-ESCO-V103 processing/output permissions; see committed source pack"
            ),
        ),
        internal_eligible=True,
        model_eligible=True,
        relevance_basis=["SYNTHETIC title match to a genuine ESCO skill; candidate only"],
        limitations=["unknown_source_date", "historical_evidence", "candidate_match_not_identity"],
        historical_context_only=True,
        language="en",
        facts={
            "verification_copy": True,
            "original_source_is_synthetic": False,
            "original_evidence_class": "occupation_requirement",
            "original_concept_uri": _ESCO_URI,
            "original_label": _ESCO_LABEL,
            "original_description_node_uri": _ESCO_DESCRIPTION_NODE,
            "taxonomy": "ESCO:v1.0.3",
            "source_pack": _ESCO_PACK,
            "source_artifact_url": _ESCO_TTL_URL,
            "source_artifact_sha256": _ESCO_TTL_SHA256,
            "source_artifact_complete": False,
            "source_description_block_sha256": _ESCO_DESCRIPTION_SHA256,
            "attribution": _ESCO_ATTRIBUTION,
            "rights_basis_url": "https://esco.ec.europa.eu/en/about-esco/faq?page=1",
            "adaptation_notice": (
                "One unmodified English skill excerpt from the adapted legacy ESCO v1.0.3 "
                "subset, copied into a synthetic verification lane. No European Commission "
                "endorsement, current taxonomy, Malaysian demand, occupation identity or "
                "university teaching assertion. Internal copy UUIDs are verification identifiers."
            ),
            "source_limitations": (
                "Publication date unknown; old edition. Complete linked English resource blocks "
                "were checked within a partial TTL retrieval; full archive integrity and "
                "completeness are not established. Engineering check is not academic validation."
            ),
        },
    )
    return EvidencePacket(
        institution_id=identity("institution"),
        programme_id=identity("programme"),
        programme_revision_id=identity("revision"),
        programme_name="SYNTHETIC Bachelor of Water Engineering",
        discipline="SYNTHETIC water engineering",
        is_synthetic=True,
        as_of=datetime.fromisoformat(_ESCO_RETRIEVED_AT),
        courses=[
            CourseEvidence(
                id=identity("course"),
                name="SYNTHETIC Irrigation Systems",
                year=1,
                course_type="UNKNOWN",
                evidence_level="title_only",
                is_verified=False,
                needs_syllabus_confirmation=True,
                reference_ids=[reference.id],
                limitations=["title_only_not_taught_content", "needs_syllabus_confirmation"],
            )
        ],
        references=[reference],
        source_policy_hash=permission_policy["sha256"],
        gaps=["SYNTHETIC institution/course only; no real curriculum or workforce evaluation"],
        limitations=[
            "SYNTHETIC verification does not measure academic accuracy",
            "One genuine ESCO legacy skill is a benchmark, never proof of course content",
            _ESCO_ATTRIBUTION,
        ],
    )


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
        # The current upstream contract does not expose an observed charge.
        "observed_cost": None,
        "observed_cost_status": "not_reported",
    }


def verify_claude(settings: Settings, *, provider_factory=ClaudeProvider) -> dict:
    """Make at most one managed request and validate one synthetic course.

    There are no repair calls, search calls, fallback providers or input document
    parameters. Failed output/exception text is not returned to logs or callers.
    """
    preflight = inspect_claude_configuration(settings)
    report = {
        "status": "blocked" if preflight["blockers"] else "failed",
        "preflight": preflight,
        "provider": "replit_claude",
        "requested_model": preflight["requested_model"],
        "actual_model": None,
        "usage": {},
        "provider_requests": 0,
        "observed_cost": None,
        "observed_cost_status": "not_reported",
        "is_synthetic": True,
        "course_count": 1,
        "citation_count": 0,
        "schema_validated": False,
        "grounding_validated": False,
        "blockers": preflight["blockers"],
    }
    if preflight["blockers"]:
        return report
    bounded = settings.model_copy(
        update={
            "analysis_provider_max_attempts": 1,
            "claude_max_output_tokens": min(
                settings.claude_max_output_tokens, VERIFICATION_MAX_OUTPUT_TOKENS
            ),
            "analysis_gemini_fallback_enabled": False,
        }
    )
    packet = _synthetic_packet(preflight["permission_policy"])
    provider = None
    try:
        provider = provider_factory(bounded)
        raw = provider.generate(packet.model_dump(mode="json"), ProgrammeResult.model_json_schema())
        report.update(_metadata(provider))
        # Distinguish schema validation from the stricter evidence validation.
        ProgrammeResult.model_validate(raw)
        report["schema_validated"] = True
        result = validate_result(raw, packet)
        if result.result_mode != "live_model":
            report["error_code"] = "live_result_mode_required"
            return report
        report["grounding_validated"] = True
        report["citation_count"] = sum(
            len(getattr(course, dimension).citations)
            for course in result.courses
            for dimension in DIMENSIONS
        )
        if not report["citation_count"]:
            report["error_code"] = "citation_check_not_exercised"
            return report
        if report["actual_model"] is None:
            report["error_code"] = "model_identity_unreported"
            return report
        if report["provider_requests"] != 1:
            report["error_code"] = "single_request_not_confirmed"
            return report
        packet_json, result_json = packet.model_dump(mode="json"), result.model_dump(mode="json")
        report.update(
            {
                "status": "live_verified",
                "availability": "verified_by_request",
                "preferred_model_used": report["actual_model"] == PREFERRED_MODEL,
                "packet_sha256": _sha256(packet_json),
                "result_sha256": _sha256(result_json),
                "evidence_packet": packet_json,
                "result": result_json,
            }
        )
    except ProviderError as exc:
        report["error_code"] = exc.code
    except (TypeError, ValueError, OverflowError, RecursionError):
        report["error_code"] = "analysis_validation_failed"
    except Exception:
        report["error_code"] = "claude_verification_failed"
    if provider is not None:
        report.update(_metadata(provider))
    return report
