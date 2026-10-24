"""Offline tests; fictional credentials/bridge/course, genuine attributed ESCO text."""

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from shiftos.core.config import Settings
from shiftos.schemas.analysis import EvidencePacket, ProgrammeResult
from shiftos.services.analysis.claude_verification import (
    inspect_claude_configuration,
    verify_claude,
)
from shiftos.services.analysis.providers import ClaudeProvider, ProviderError
from shiftos.services.analysis.validation import offline_result, validate_result


@pytest.fixture
def configured(tmp_path):
    policy = tmp_path / "synthetic_test_permissions.json"
    policy.write_text(
        json.dumps(
            {
                "version": "synthetic-test-policy-1",
                "sources": {
                    "C-ESCO-V103": {
                        "internal_analysis_allowed": True,
                        "external_model_allowed": True,
                        "excerpt_output_allowed": True,
                        "basis": "Explicit test-only allow policy for the permitted ESCO source",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return Settings(
        _env_file=None,
        claude_enabled=True,
        analysis_external_processing_allowed=True,
        replit_anthropic_api_key="SYNTHETIC_managed_test_credential",
        replit_anthropic_base_url="https://synthetic-bridge.example.invalid/private-route",
        claude_model="claude-opus-5",
        analysis_provider_max_attempts=3,
        analysis_gemini_fallback_enabled=True,
        analysis_permissions_path=policy,
    )


class SyntheticProvider:
    """In-memory provider fake: no HTTP client or external request is created."""

    def __init__(self, settings):
        self.settings = settings
        self.request_attempts = 0
        self.last_response_metadata = {}

    def generate(self, packet, response_schema):
        assert response_schema == ProgrammeResult.model_json_schema()
        self.packet = EvidencePacket.model_validate(packet)
        self.request_attempts += 1
        self.last_response_metadata = {
            "actual_model": "claude-opus-5",
            "usage": {"input_tokens": 100, "output_tokens": 250},
            "request_count": 1,
            "observed_cost": None,
        }
        result = offline_result(self.packet).model_dump(mode="json")
        result["result_mode"] = "live_model"
        return result


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("claude_enabled", False, "claude_disabled"),
        ("analysis_external_processing_allowed", False, "external_processing_not_approved"),
        ("replit_anthropic_api_key", None, "managed_credential_missing"),
        ("replit_anthropic_base_url", None, "managed_base_url_missing"),
        ("replit_anthropic_base_url", "https://api.anthropic.com", "managed_base_url_invalid"),
        ("claude_model", "bad-model", "claude_model_invalid"),
    ],
)
def test_preflight_blockers_prevent_provider_construction(configured, field, value, reason):
    settings = configured.model_copy(update={field: value})

    def forbidden_factory(_settings):
        pytest.fail("Blocked preflight must not construct a provider")

    result = verify_claude(settings, provider_factory=forbidden_factory)
    assert result["status"] == "blocked"
    assert reason in result["blockers"]
    assert result["provider_requests"] == result["preflight"]["provider_requests"] == 0
    assert result["preflight"]["availability"] == "not_verified"


def test_preflight_does_not_claim_replit_availability_or_expose_managed_values(configured):
    result = inspect_claude_configuration(configured)
    assert result["status"] == "configuration_ready"
    assert result["availability"] == "not_verified"
    assert result["provider_requests"] == 0
    assert result["preferred_model_configured"]
    assert not result["selected_for_analysis"]  # Explicit verification can precede selection.
    assert result["managed_credential_present"] and result["managed_base_url_valid"]
    serialized = json.dumps(result)
    assert "SYNTHETIC_managed_test_credential" not in serialized
    assert "synthetic-bridge.example.invalid" not in serialized
    assert "private-route" not in serialized


def test_one_synthetic_course_uses_real_schema_grounding_and_bounded_settings(configured):
    instances = []

    def factory(settings):
        instances.append(SyntheticProvider(settings))
        return instances[-1]

    result = verify_claude(configured, provider_factory=factory)
    assert result["status"] == "live_verified"
    assert result["schema_validated"] and result["grounding_validated"]
    assert result["provider_requests"] == 1
    assert result["citation_count"] >= 1
    assert result["actual_model"] == result["requested_model"] == "claude-opus-5"
    assert result["usage"] == {"input_tokens": 100, "output_tokens": 250}
    assert result["observed_cost"] is None
    assert result["observed_cost_status"] == "not_reported"
    assert len(result["packet_sha256"]) == len(result["result_sha256"]) == 64
    provider = instances[0]
    assert len(instances) == provider.request_attempts == 1
    assert provider.settings.analysis_provider_max_attempts == 1
    assert provider.settings.claude_max_output_tokens == 4096
    assert not provider.settings.analysis_gemini_fallback_enabled
    assert configured.analysis_provider_max_attempts == 3  # Caller configuration is unchanged.
    assert configured.analysis_gemini_fallback_enabled
    packet = EvidencePacket.model_validate(result["evidence_packet"])
    assert packet.is_synthetic and len(packet.courses) == 1
    assert packet.courses[0].name.startswith("SYNTHETIC ")
    assert packet.courses[0].evidence_level == "title_only"
    assert packet.courses[0].needs_syllabus_confirmation
    assert all(ref.evidence_class == "synthetic_demo" for ref in packet.references)
    assert all(ref.is_synthetic and ref.facts["verification_copy"] for ref in packet.references)
    assert all(not ref.facts["original_source_is_synthetic"] for ref in packet.references)
    validate_result(result["result"], packet)


def test_citation_is_exact_genuine_committed_esco_skill_not_a_fabricated_authority(configured):
    report = verify_claude(configured, provider_factory=SyntheticProvider)
    packet = EvidencePacket.model_validate(report["evidence_packet"])
    reference = packet.references[0]
    pack = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "data/reference_packs/esco-v1.0.3.subset.reviewed.json"
        ).read_text(encoding="utf-8")
    )
    original = next(row for row in pack["records"] if row["key"] == reference.source_url)
    assert original["kind"] == reference.kind == "skill"
    assert reference.source_url == reference.facts["original_concept_uri"] == original["key"]
    assert str(reference.record_id) == original["key"].rsplit("/", 1)[1]
    assert reference.excerpt == original["excerpt"]
    assert reference.excerpt == original["data"]["label"] + ": " + original["data"]["description"]
    assert reference.locator == original["locator"]
    assert reference.publisher == pack["metadata"]["publisher"]
    assert reference.retrieved_at == datetime.fromisoformat(
        pack["metadata"]["original_retrieved_at"]
    )
    assert reference.publication_date is None and reference.date_precision == "unknown"
    assert reference.historical_context_only and packet.as_of >= reference.retrieved_at
    assert (
        reference.facts["original_description_node_uri"]
        == (original["data"]["metadata_json"]["description_node_uri"])
    )
    assert (
        reference.facts["source_description_block_sha256"]
        == (original["data"]["metadata_json"]["description_resource_block_sha256"])
    )
    assert reference.facts["taxonomy"] == original["data"]["taxonomy"]
    assert reference.facts["attribution"] == pack["metadata"]["attribution"]
    artifact = next(item for item in pack["metadata"]["original_artifacts"] if not item["complete"])
    assert reference.facts["source_artifact_url"] == artifact["url"]
    assert reference.facts["source_artifact_sha256"] == artifact["sha256"]
    assert reference.facts["source_artifact_complete"] is False
    assert reference.facts["original_evidence_class"] == "occupation_requirement"
    assert reference.scope == "occupation_benchmark"
    assert "synthetic verification copy" in reference.title
    assert "no real authority" not in reference.publisher
    finding = report["result"]["courses"][0]["foundational_relevance"]
    assert "unknown_source_date" in finding["limitations"]
    assert "historical_evidence" in finding["limitations"]


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "malformed",
        "too_large",
        "missing_source",
        "blank_basis",
        "internal_denied",
        "model_denied",
        "output_denied",
        "numeric_grant",
    ],
)
def test_real_esco_quote_requires_explicit_bounded_source_permissions(configured, change):
    path = configured.analysis_permissions_path
    policy = json.loads(path.read_text(encoding="utf-8"))
    rule = policy["sources"]["C-ESCO-V103"]
    if change == "missing":
        path.unlink()
    elif change == "malformed":
        path.write_text("[]", encoding="utf-8")
    elif change == "too_large":
        path.write_text(" " * 100_001, encoding="utf-8")
    else:
        if change == "missing_source":
            policy["sources"] = {}
        elif change == "blank_basis":
            rule["basis"] = "  "
        else:
            flag = {
                "internal_denied": "internal_analysis_allowed",
                "model_denied": "external_model_allowed",
                "output_denied": "excerpt_output_allowed",
                "numeric_grant": "external_model_allowed",
            }[change]
            rule[flag] = 1 if change == "numeric_grant" else False
        path.write_text(json.dumps(policy), encoding="utf-8")

    def forbidden_factory(_settings):
        pytest.fail("Real source permission failure must precede provider construction")

    result = verify_claude(configured, provider_factory=forbidden_factory)
    assert result["status"] == "blocked"
    assert result["provider_requests"] == 0
    assert not result["preflight"]["esco_processing_permitted"]
    assert any(reason.startswith("esco_") for reason in result["blockers"])


@pytest.mark.parametrize(
    "change,error",
    [
        ("fabricated_quote", "analysis_validation_failed"),
        ("extra_course", "analysis_validation_failed"),
        ("offline_mode", "live_result_mode_required"),
        ("no_citations", "citation_check_not_exercised"),
        ("missing_model", "model_identity_unreported"),
    ],
)
def test_invalid_or_unverified_output_fails_without_repairs(configured, change, error):
    class InvalidProvider(SyntheticProvider):
        def generate(self, packet, response_schema):
            result = super().generate(packet, response_schema)
            if change == "fabricated_quote":
                result["courses"][0]["foundational_relevance"]["citations"][0]["quote"] = (
                    "SYNTHETIC malicious invented teaching statistic"
                )
            elif change == "extra_course":
                result["courses"].append(deepcopy(result["courses"][0]))
            elif change == "offline_mode":
                result["result_mode"] = "offline_synthetic"
            elif change == "no_citations":
                for value in result["courses"][0].values():
                    if isinstance(value, dict) and "citations" in value:
                        value["citations"] = []
            else:
                self.last_response_metadata["actual_model"] = None
            return result

    result = verify_claude(configured, provider_factory=InvalidProvider)
    assert result["status"] == "failed"
    assert result["error_code"] == error
    assert result["provider_requests"] == 1
    assert "result" not in result and "evidence_packet" not in result
    assert "malicious" not in json.dumps(result)


@pytest.mark.parametrize("failure", ["auth", "unsafe_message", "constructor"])
def test_provider_failures_are_sanitized_and_never_retried(configured, failure):
    instances = []

    class FailedProvider(SyntheticProvider):
        def generate(self, packet, response_schema):
            super().generate(packet, response_schema)
            if failure == "auth":
                raise ProviderError("provider_authentication_failed")
            raise RuntimeError("SYNTHETIC_managed_test_credential private-route raw body")

    def factory(settings):
        if failure == "constructor":
            raise RuntimeError("SYNTHETIC_managed_test_credential")
        instances.append(FailedProvider(settings))
        return instances[-1]

    result = verify_claude(configured, provider_factory=factory)
    assert result["status"] == "failed"
    assert result["error_code"] == (
        "provider_authentication_failed" if failure == "auth" else "claude_verification_failed"
    )
    assert result["provider_requests"] == (0 if failure == "constructor" else 1)
    assert len(instances) <= 1
    serialized = json.dumps(result)
    assert "SYNTHETIC_managed_test_credential" not in serialized
    assert "private-route" not in serialized
    assert "raw body" not in serialized


def test_untrusted_usage_and_model_metadata_are_not_echoed(configured):
    class MetadataProvider(SyntheticProvider):
        def generate(self, packet, response_schema):
            result = super().generate(packet, response_schema)
            self.last_response_metadata.update(
                {
                    "actual_model": "claude-opus-4-8",
                    "usage": {
                        "input_tokens": True,
                        "output_tokens": -1,
                        "cache_read_input_tokens": 12,
                        "unknown": "private-route",
                    },
                    "observed_cost": {"amount": "invented", "currency": "USD"},
                }
            )
            return result

    result = verify_claude(configured, provider_factory=MetadataProvider)
    assert result["status"] == "live_verified"
    assert not result["preferred_model_used"]
    assert result["actual_model"] == "claude-opus-4-8"
    assert result["usage"] == {"cache_read_input_tokens": 12}
    assert result["observed_cost"] is None
    assert "invented" not in json.dumps(result)


def test_actual_adapter_has_one_transport_attempt_on_rate_limit(configured):
    calls = []

    def response(request):
        calls.append(request)
        assert request.url.path == "/private-route/v1/messages"
        body = json.loads(request.content)
        assert body["max_tokens"] == 4096
        assert body["model"] == "claude-opus-5"
        packet = json.loads(body["messages"][0]["content"])
        assert packet["is_synthetic"] and len(packet["courses"]) == 1
        return httpx.Response(429, headers={"Retry-After": "0"})

    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        result = verify_claude(
            configured,
            provider_factory=lambda settings: ClaudeProvider(settings, client=client),
        )
    assert result["status"] == "failed"
    assert result["error_code"] == "provider_rate_limited"
    assert result["provider_requests"] == len(calls) == 1
    assert result["observed_cost"] is None
