"""Offline Gemini transport/verification checks; no real provider request or bill."""

import json
from copy import deepcopy

import httpx
import pytest
from pydantic import ValidationError
from test_analysis_claude_verification import configured as claude_configured  # noqa: F401
from test_analysis_providers import gemini_reply, settings

from shiftos.schemas.analysis import EvidencePacket, ProgrammeResult
from shiftos.services.analysis.claude_verification import _sha256, _synthetic_packet
from shiftos.services.analysis.gemini_verification import (
    inspect_gemini_configuration,
    verify_gemini,
)
from shiftos.services.analysis.providers import GeminiProvider, ProviderError
from shiftos.services.analysis.validation import offline_result


@pytest.mark.parametrize("level", ["low", "medium", "high"])
def test_configurable_thinking_uses_stateless_interactions_only(level):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=gemini_reply())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = GeminiProvider(settings(gemini_thinking_level=level), client)
        assert provider.generate({"synthetic": True}, {"type": "object"}) == {"synthetic": True}
    body = json.loads(requests[0].content)
    assert requests[0].url.path == "/v1beta/interactions"
    assert body["generation_config"]["thinking_level"] == level
    assert body["generation_config"]["max_output_tokens"] == 32768
    assert body["generation_config"]["tool_choice"] == "none"
    assert body["store"] is body["stream"] is body["background"] is False
    assert not set(body) & {"tools", "agent", "previous_interaction_id", "generationConfig"}
    assert not set(body["generation_config"]) & {"temperature", "top_p", "top_k"}
    assert provider.last_response_metadata["thinking_level"] == level
    assert provider.last_response_metadata["api"] == "interactions"
    assert provider.last_response_metadata["timeout_seconds"] == 180
    assert provider.last_response_metadata["latency_seconds"] >= 0


@pytest.mark.parametrize("value", ["minimal", "unbounded", "MEDIUM"])
def test_argon_thinking_rejects_unsupported_values(value):
    with pytest.raises(ValidationError):
        settings(gemini_thinking_level=value)


@pytest.mark.parametrize("value", [0, 301])
def test_argon_timeout_is_bounded(value):
    with pytest.raises(ValidationError):
        settings(gemini_timeout_seconds=value)


@pytest.mark.parametrize(
    "status", ["in_progress", "requires_action", "failed", "cancelled", "incomplete", None]
)
def test_incomplete_interactions_fail_without_polling_and_keep_usage(status):
    response = gemini_reply()
    response["status"] = status
    response["usage"] = {"total_input_tokens": 10, "total_output_tokens": 20}
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=response)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = GeminiProvider(settings(), client)
        with pytest.raises(ProviderError) as error:
            provider.generate({}, {})
    assert error.value.code == "model_output_incomplete"
    assert len(requests) == 1
    assert provider.last_response_metadata["usage"] == {"input_tokens": 10, "output_tokens": 20}


def test_different_returned_gemini_model_is_not_silently_accepted():
    response = gemini_reply()
    response["model"] = "gemini-other-synthetic-model"
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))
    ) as c:
        provider = GeminiProvider(settings(), c)
        with pytest.raises(ProviderError) as error:
            provider.generate({}, {})
    assert error.value.code == "provider_model_mismatch"
    assert provider.last_response_metadata["actual_model"] == "gemini-other-synthetic-model"


@pytest.mark.parametrize(
    "kind", ["function_call", "google_search_call", "url_context_call", "user_input"]
)
def test_unrequested_steps_rejected_even_with_valid_json_output(kind):
    response = gemini_reply()
    response["steps"].insert(0, {"type": kind, "content": []})
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))
    ) as c:
        with pytest.raises(ProviderError) as error:
            GeminiProvider(settings(), c).generate({}, {})
    assert error.value.code == "provider_response_invalid"


def test_prior_generate_content_envelope_is_not_interpreted_as_interactions():
    legacy = {"modelVersion": "gemini-3.1-flash-lite", "candidates": []}
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=legacy))
    ) as c:
        with pytest.raises(ProviderError) as error:
            GeminiProvider(settings(), c).generate({}, {})
    assert error.value.code == "provider_response_invalid"


def test_gemini_timeout_honours_remaining_worker_deadline():
    clock = [0.0]
    seen = []

    def handler(request):
        seen.append(request.extensions["timeout"])
        clock[0] = 8.0
        return httpx.Response(200, json=gemini_reply())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = GeminiProvider(
            settings(gemini_timeout_seconds=180), client, monotonic=lambda: clock[0]
        )
        provider.deadline = 7.0
        with pytest.raises(ProviderError) as error:
            provider.generate({}, {})
    assert error.value.code == "provider_deadline"
    assert all(timeout <= 7 for timeout in seen[0].values())


def test_gemini_audit_metadata_rejects_unsafe_shapes():
    from shiftos.services.analysis.orchestrator import _response_metadata

    provider = type(
        "SyntheticMetadata",
        (),
        {
            "last_response_metadata": {
                "api": "interactions",
                "thinking_level": ["medium"],
                "max_output_tokens": True,
                "timeout_seconds": 10**9,
                "latency_seconds": float("nan"),
                "api_key": "SYNTHETIC-private-secret",
            }
        },
    )()
    audit = _response_metadata(
        provider, provider_name="gemini_direct", requested_model="gemini-4-argon", status="returned"
    )
    assert audit["api"] == "interactions"
    assert not set(audit) & {
        "thinking_level",
        "max_output_tokens",
        "timeout_seconds",
        "latency_seconds",
        "api_key",
    }
    assert "SYNTHETIC-private" not in json.dumps(audit)


@pytest.fixture
def configured(claude_configured):  # noqa: F811
    return claude_configured.model_copy(
        update={
            "gemini_enabled": True,
            "gemini_model": "gemini-4-argon",
            "gemini_api_key": claude_configured.replit_anthropic_api_key,
        }
    )


def synthetic_transport(configured, *, mutate=None, status=200):
    requests, instances = [], []

    def handler(request):
        requests.append(request)
        if status != 200:
            return httpx.Response(status, text="SYNTHETIC-private-upstream-error")
        body = json.loads(request.content)
        packet = EvidencePacket.model_validate_json(body["input"])
        result = offline_result(packet).model_dump(mode="json")
        result["result_mode"] = "live_model"
        response = gemini_reply(json.dumps(result))
        response["model"] = "gemini-4-argon"
        response["usage"] = {
            "total_input_tokens": 100,
            "total_output_tokens": 250,
            "total_thought_tokens": 30,
            "total_tokens": 380,
        }
        if mutate:
            mutate(response, result)
        return httpx.Response(200, json=response)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    def factory(bounded):
        instance = GeminiProvider(bounded, client, sleep=lambda _: None)
        instances.append(instance)
        return instance

    return client, factory, requests, instances


@pytest.mark.parametrize(
    "field,value,blocker",
    [
        ("gemini_enabled", False, "gemini_disabled"),
        ("analysis_external_processing_allowed", False, "external_processing_not_approved"),
        ("gemini_api_key", None, "gemini_credential_missing"),
        ("gemini_model", "", "gemini_model_missing_or_invalid"),
        ("gemini_model", "../bad-model", "gemini_model_missing_or_invalid"),
    ],
)
def test_blocked_preflight_never_constructs_provider(configured, field, value, blocker):
    def forbidden(_settings):
        pytest.fail("Blocked configuration cannot construct a provider")

    report = verify_gemini(configured.model_copy(update={field: value}), provider_factory=forbidden)
    assert report["status"] == "blocked" and blocker in report["blockers"]
    assert report["provider_requests"] == 0
    assert report["actual_model"] is report["provider_latency_seconds"] is None


def test_preflight_reports_no_account_availability_or_credentials(configured):
    report = inspect_gemini_configuration(configured)
    assert report["status"] == "configuration_ready" and report["provider_requests"] == 0
    assert report["availability"] == "not_verified" and report["preferred_model_configured"]
    assert "SYNTHETIC_managed_test_credential" not in json.dumps(report)


@pytest.mark.parametrize("policy_change", ["deny", "missing", "corrupt"])
def test_source_permissions_fail_closed_before_model_construction(configured, policy_change):
    path = configured.analysis_permissions_path
    if policy_change == "deny":
        policy = json.loads(path.read_text(encoding="utf-8"))
        policy["sources"]["C-ESCO-V103"]["external_model_allowed"] = False
        path.write_text(json.dumps(policy), encoding="utf-8")
    elif policy_change == "missing":
        path.unlink()
    else:
        path.write_text("invalid JSON", encoding="utf-8")

    def forbidden(_settings):
        pytest.fail("Denied source must not reach a provider")

    report = verify_gemini(configured, provider_factory=forbidden)
    assert report["status"] == "blocked" and report["provider_requests"] == 0
    assert any(reason.startswith("esco_") for reason in report["blockers"])


def test_exact_claude_packet_schema_grounding_and_token_accounting(configured):
    client, factory, requests, instances = synthetic_transport(configured)
    with client:
        report = verify_gemini(configured, provider_factory=factory)
    assert report["status"] == "live_verified"  # Mocked result only; no live claim in docs.
    assert report["schema_validated"] and report["grounding_validated"]
    assert report["insufficient_evidence_validated"] and report["citation_count"] >= 1
    assert report["provider_requests"] == len(requests) == 1
    assert report["actual_model"] == report["requested_model"] == "gemini-4-argon"
    assert report["usage"] == {
        "input_tokens": 100,
        "output_tokens": 250,
        "thought_tokens": 30,
        "total_tokens": 380,
    }
    assert report["observed_cost"] is None and report["provider_latency_seconds"] >= 0
    expected_packet = _synthetic_packet(report["preflight"]["permission_policy"])
    assert report["evidence_packet"] == expected_packet.model_dump(mode="json")
    assert report["packet_sha256"] == _sha256(expected_packet.model_dump(mode="json"))
    assert report["schema_sha256"] == _sha256(ProgrammeResult.model_json_schema())
    body = json.loads(requests[0].content)
    assert body["response_format"][0]["schema"] == ProgrammeResult.model_json_schema()
    assert body["generation_config"]["max_output_tokens"] == 32768
    assert body["generation_config"]["thinking_level"] == "medium"
    assert body["generation_config"]["thinking_summaries"] == "none"
    assert "tools" not in body and "SYNTHETIC" in body["input"]
    assert body["store"] is False
    bounded = instances[0].settings
    assert bounded.analysis_provider_max_attempts == 1
    assert not bounded.research_enabled and not bounded.analysis_gemini_fallback_enabled
    assert configured.analysis_provider_max_attempts == 3
    assert configured.gemini_max_output_tokens == 32768


@pytest.mark.parametrize("failure", ["schema", "citation", "title_claim", "no_citation", "usage"])
def test_invalid_output_retains_usage_without_publishing_result(configured, failure):
    def mutate(response, result):
        course = result["courses"][0]
        if failure == "schema":
            result["fabricated_score"] = 99
        elif failure == "citation":
            course["foundational_relevance"]["citations"][0]["quote"] = "Invented academic claim"
        elif failure == "title_claim":
            course["curriculum_currency"]["status"] = "monitor"
        elif failure == "no_citation":
            for dimension in (
                "foundational_relevance",
                "ai_transformation",
                "workforce_alignment",
                "curriculum_currency",
                "future_resilience",
            ):
                course[dimension]["citations"] = []
        elif failure == "usage":
            response["usage"] = {"total_input_tokens": True, "total_output_tokens": -1}
        response["steps"][0]["content"][0]["text"] = json.dumps(result)

    client, factory, requests, _ = synthetic_transport(configured, mutate=mutate)
    with client:
        report = verify_gemini(configured, provider_factory=factory)
    assert report["status"] == "failed" and report["provider_requests"] == len(requests) == 1
    assert "result" not in report and "Invented academic claim" not in json.dumps(report)
    assert report["actual_model"] == "gemini-4-argon"
    if failure == "usage":
        assert report["error_code"] == "token_usage_unreported" and report["usage"] == {}
    else:
        assert report["usage"]["output_tokens"] == 250


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "provider_authentication_failed"),
        (429, "provider_rate_limited"),
        (503, "provider_unavailable"),
    ],
)
def test_verification_makes_one_attempt_even_for_retryable_errors(configured, status, code):
    client, factory, requests, _ = synthetic_transport(configured, status=status)
    with client:
        report = verify_gemini(configured, provider_factory=factory)
    assert report["status"] == "failed" and report["error_code"] == code
    assert report["provider_requests"] == len(requests) == 1
    assert "SYNTHETIC-private" not in json.dumps(report)


@pytest.mark.parametrize("model", [None, "claude-synthetic-test", "https://private.invalid/key"])
def test_response_requires_actual_gemini_identity(model):
    response = gemini_reply()
    response["model"] = model
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))
    ) as c:
        provider = GeminiProvider(settings(), c)
        with pytest.raises(ProviderError) as error:
            provider.generate({}, {})
    assert error.value.code == "provider_response_invalid"
    assert provider.last_response_metadata["actual_model"] is None


@pytest.mark.parametrize(
    "parts",
    [
        [],
        {},
        ["bad"],
        [{"type": "text", "text": "{}", "thought": "false"}],
        [{"type": "text", "text": "{}", "function_call": {"name": "unapproved"}}],
        [{"type": "function_call", "name": "unapproved"}],
    ],
)
def test_malformed_and_tool_parts_are_rejected(parts):
    response = deepcopy(gemini_reply())
    response["steps"][0]["content"] = parts
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))
    ) as c:
        with pytest.raises(ProviderError) as error:
            GeminiProvider(settings(), c).generate({}, {})
    assert error.value.code == "provider_response_invalid"


def test_thoughts_are_discarded_and_usage_survives_truncated_response():
    response = gemini_reply()
    response["steps"].insert(
        0,
        {
            "type": "thought",
            "summary": [
                {"type": "text", "text": "SYNTHETIC thinking must not enter the JSON result"}
            ],
            "signature": "synthetic-signature",
        },
    )
    response["usage"] = {"total_input_tokens": 12, "total_output_tokens": 3}
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))
    ) as c:
        provider = GeminiProvider(settings(gemini_max_output_tokens=100), c)
        assert provider.generate({}, {}) == {"synthetic": True}
        response["status"] = "incomplete"
        with pytest.raises(ProviderError) as error:
            provider.generate({}, {})
    assert error.value.code == "model_output_incomplete"
    assert provider.last_response_metadata["usage"] == {"input_tokens": 12, "output_tokens": 3}


@pytest.mark.parametrize("limit", [0, 65537])
def test_output_budget_must_stay_bounded(limit):
    with pytest.raises(ValidationError):
        settings(gemini_max_output_tokens=limit)
