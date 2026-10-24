"""Mocked Brave responses only: bounded usage metadata never proves live research."""

import json

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select
from test_analysis_providers import SECRET, settings
from test_analysis_research import (
    SOURCE,
    research_setup,  # noqa: F401 - isolated research fixture
    runner,
)

from shiftos.models.analysis import ResearchCache
from shiftos.services.analysis.providers import BRAVE_ENDPOINT, BraveSearch, ProviderError
from shiftos.services.analysis.research import ResearchService

QUERY = "official engineering workforce SYNTHETIC_QUERY_CANARY"
BODY_CANARY = "SYNTHETIC_UNTRUSTED_RESPONSE_BODY_DO_NOT_RETAIN"
HEADER_CANARY = "SYNTHETIC_UNTRUSTED_RESPONSE_HEADER_DO_NOT_RETAIN"


@pytest.fixture(autouse=True)
def forbid_real_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Brave usage tests must use MockTransport, never real network requests")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def configured(**overrides):
    return settings(
        gemini_enabled=False,
        analysis_provider_max_attempts=1,
        **overrides,
    )


def assert_private_metadata(metadata):
    encoded = json.dumps(metadata)
    for private in (SECRET, QUERY, BODY_CANARY, HEADER_CANARY):
        assert private not in encoded
    assert "https://" not in encoded
    assert metadata["provider"] == "brave"
    assert metadata["observed_cost"] is None
    assert metadata["duration_ms"] >= 0


def test_brave_success_reports_actual_attempt_and_counts_without_retaining_search_text():
    seen = []
    rows = [
        {
            "title": "First institutional pointer",
            "url": "https://OFFICIAL.invalid/report/?b=2&a=1#section",
            "description": BODY_CANARY,
        },
        {"title": "Duplicate", "url": "https://official.invalid/report?a=1&b=2"},
        {"title": "Other publication", "url": "https://official.invalid/other"},
        {"title": "Insecure", "url": "http://official.invalid/report"},
        {"title": "Secret query", "url": "https://official.invalid/data?token=private"},
        {"title": "Malformed pointer", "url": None},
    ]

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={"web": {"results": rows}, "untrusted_extra": BODY_CANARY},
            headers={
                "X-RateLimit-Limit": "1, 15000",
                "X-RateLimit-Policy": "1;w=1, 15000;w=2592000",
                "X-RateLimit-Remaining": "0, 14999",
                "X-RateLimit-Reset": "1, 2591999",
                "X-Untrusted-Header": HEADER_CANARY,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = BraveSearch(configured(), client)
        pointers = provider.search(QUERY)
    assert pointers == [
        {"title": rows[0]["title"], "url": rows[0]["url"]},
        {"title": rows[2]["title"], "url": rows[2]["url"]},
    ]
    assert len(seen) == 1
    assert str(seen[0].url).startswith(BRAVE_ENDPOINT + "?")
    assert seen[0].headers["X-Subscription-Token"] == SECRET
    assert seen[0].url.params["extra_snippets"] == "false"
    assert seen[0].url.params["summary"] == "false"
    metadata = provider.last_response_metadata
    assert metadata["http_status"] == 200
    assert metadata["request_count"] == 1
    assert metadata["result_count"] == 6
    assert metadata["pointer_count"] == 2
    assert set(metadata["quota"]) == {"limit", "policy", "remaining", "reset"}
    assert_private_metadata(metadata)
    assert BODY_CANARY not in json.dumps(pointers)


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "provider_response_invalid"),
        (401, "provider_authentication_failed"),
        (403, "provider_authentication_failed"),
        (429, "provider_rate_limited"),
        (500, "provider_unavailable"),
    ],
)
def test_brave_failure_captures_safe_status_with_no_retry_or_response_body(status, code):
    requests, sleeps = [], []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            status,
            text=BODY_CANARY + SECRET,
            headers={
                "Retry-After": "1",
                "X-RateLimit-Remaining": "0",
                "X-Untrusted-Header": HEADER_CANARY,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = BraveSearch(configured(), client, sleep=sleeps.append)
        with pytest.raises(ProviderError) as error:
            provider.search(QUERY)
    assert error.value.code == code
    assert len(requests) == 1 and sleeps == []
    assert provider.last_response_metadata["http_status"] == status
    assert provider.last_response_metadata["request_count"] == 1
    assert provider.last_response_metadata["error_code"] == code
    assert_private_metadata(provider.last_response_metadata)
    assert SECRET not in str(error.value) and BODY_CANARY not in str(error.value)


def test_brave_quota_header_canaries_and_unrelated_headers_are_not_retained():
    def handler(_):
        return httpx.Response(
            200,
            json={"web": {"results": []}},
            headers={
                "X-RateLimit-Limit": HEADER_CANARY,
                "X-RateLimit-Policy": "1;w=1, " + HEADER_CANARY,
                "X-RateLimit-Remaining": "0, " + SECRET,
                "X-RateLimit-Reset": "1, https://private.invalid",
                "Authorization": SECRET,
                "Set-Cookie": HEADER_CANARY,
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = BraveSearch(configured(), client)
        assert provider.search(QUERY) == []
    assert provider.last_response_metadata["quota"] == {}
    assert_private_metadata(provider.last_response_metadata)


def test_brave_metadata_resets_between_invocations_instead_of_reusing_error_or_quota():
    count = 0

    def handler(_):
        nonlocal count
        count += 1
        if count == 1:
            return httpx.Response(429, text=BODY_CANARY, headers={"X-RateLimit-Remaining": "0"})
        return httpx.Response(200, json={"web": {"results": []}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = BraveSearch(configured(), client)
        with pytest.raises(ProviderError):
            provider.search(QUERY)
        first_metadata = provider.last_response_metadata.copy()
        assert provider.search("official engineering competencies") == []
    assert first_metadata["http_status"] == 429
    assert first_metadata["error_code"] == "provider_rate_limited"
    metadata = provider.last_response_metadata
    assert metadata["http_status"] == 200
    assert metadata["request_count"] == 1 and provider.request_attempts == 2
    assert metadata["result_count"] == metadata["pointer_count"] == 0
    assert metadata["quota"] == {}
    assert metadata.get("error_code") is None
    assert_private_metadata(metadata)


@pytest.mark.parametrize("overrides", [{"research_enabled": False}, {"brave_search_api_key": None}])
def test_brave_unconfigured_search_records_zero_actual_http_requests(overrides):
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("No external search is configured"))
    ) as client:
        provider = BraveSearch(configured(**overrides), client)
        with pytest.raises(ProviderError) as error:
            provider.search(QUERY)
    assert error.value.code == "search_not_configured"
    assert provider.last_response_metadata["request_count"] == 0
    assert provider.last_response_metadata["error_code"] == "search_not_configured"
    assert provider.last_response_metadata.get("http_status") is None
    assert_private_metadata(provider.last_response_metadata)


def test_brave_malformed_success_body_retains_status_but_no_raw_output():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={"web": {"results": BODY_CANARY}},
                headers={"X-Untrusted-Header": HEADER_CANARY},
            )
        )
    ) as client:
        provider = BraveSearch(configured(), client)
        with pytest.raises(ProviderError) as error:
            provider.search(QUERY)
    assert error.value.code == "provider_response_invalid"
    assert provider.last_response_metadata["http_status"] == 200
    assert provider.last_response_metadata["request_count"] == 1
    assert provider.last_response_metadata["error_code"] == "provider_response_invalid"
    assert_private_metadata(provider.last_response_metadata)


def test_research_cache_hit_counts_no_new_request_or_stale_provider_metadata(
    database,
    research_setup,  # noqa: F811 - imported fixture
):
    configured_settings, fixture, _, _ = research_setup
    configured_settings.brave_search_api_key = SecretStr(SECRET)
    configured_settings.analysis_provider_max_attempts = 1
    requests, imports = [], []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [{"title": BODY_CANARY, "url": SOURCE, "description": BODY_CANARY}]
                }
            },
            headers={"X-RateLimit-Remaining": "49", "X-Untrusted-Header": HEADER_CANARY},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = BraveSearch(configured_settings, client)
        service = ResearchService(
            database, configured_settings, lambda _: provider, runner(fixture, imports)
        )
        first = service.run("accounting", ["missing_workforce"])
        second = service.run("accounting", ["missing_workforce"])
    assert first["status"] == second["status"] == "VERIFIED_IMPORTS_AVAILABLE"
    assert first["version_ids"] == second["version_ids"]
    assert len(requests) == len(imports) == 1
    assert first["search_request_count"] == 1
    assert second["search_request_count"] == 0
    assert first["query_count"] == second["query_count"] == 1
    metadata = first["attempts"][0]["search_metadata"]
    assert metadata["request_count"] == 1 and metadata["http_status"] == 200
    assert metadata["result_count"] == metadata["pointer_count"] == 1
    assert metadata["quota"] == {"remaining": "49"}
    assert_private_metadata(metadata)
    assert second["attempts"][0]["cached"] is True
    assert "search_metadata" not in second["attempts"][0]
    with database.session_factory() as session:
        cached = json.dumps(session.scalar(select(ResearchCache)).response_json)
    for forbidden in (SECRET, BODY_CANARY, HEADER_CANARY, SOURCE, "pointers", "description"):
        assert forbidden not in cached


def test_research_negative_cache_reports_zero_new_paid_attempts_and_no_error_body(
    database,
    research_setup,  # noqa: F811 - imported fixture
):
    configured_settings, fixture, _, _ = research_setup
    configured_settings.brave_search_api_key = SecretStr(SECRET)
    configured_settings.analysis_provider_max_attempts = 1
    requests, imports = [], []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            429,
            text=BODY_CANARY + SECRET,
            headers={"X-RateLimit-Remaining": "0", "Retry-After": "30"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = BraveSearch(configured_settings, client)
        service = ResearchService(
            database, configured_settings, lambda _: provider, runner(fixture, imports)
        )
        first = service.run("accounting", ["missing_workforce"])
        second = service.run("accounting", ["missing_workforce"])
    assert first["status"] == second["status"] == "PROVIDER_UNAVAILABLE"
    assert first["version_ids"] == second["version_ids"] == []
    assert len(requests) == 1 and imports == []
    assert first["search_request_count"] == 1 and second["search_request_count"] == 0
    metadata = first["attempts"][0]["search_metadata"]
    assert metadata["http_status"] == 429
    assert metadata["error_code"] == "provider_rate_limited"
    assert_private_metadata(metadata)
    assert "search_metadata" not in second["attempts"][0]
    with database.session_factory() as session:
        cached = json.dumps(session.scalar(select(ResearchCache)).response_json)
    assert SECRET not in cached and BODY_CANARY not in cached
