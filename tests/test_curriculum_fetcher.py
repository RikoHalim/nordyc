"""Offline safety/behaviour checks; no official site is contacted."""

import hashlib
import traceback
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from shiftos.services.ingestion.fetcher import (
    FetchError,
    SafeFetcher,
    _PinnedHTTPTransport,
)

BASE = "https://www.xmu.edu.my"
PAGE = f"{BASE}/undergraduate-programmes"
ROBOTS = "User-agent: *\nDisallow: /private\n"
PUBLIC_IP = "93.184.216.34"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, duration: float) -> None:
        self.sleeps.append(duration)
        self.now += duration


def make_fetcher(handler, **kwargs):
    clock = FakeClock()
    return SafeFetcher(
        {"www.xmu.edu.my", "xmu.edu.my"},
        enabled=True,
        terms_reviewed=True,
        transport=httpx.MockTransport(handler),
        resolver=kwargs.pop("resolver", lambda _: [PUBLIC_IP]),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        **kwargs,
    ), clock


def robots_response(text=ROBOTS, status=200):
    return httpx.Response(status, text=text, headers={"Content-Type": "text/plain"})


def html_response(text="<html><h1>Example</h1></html>", **kwargs):
    return httpx.Response(200, text=text, headers={"Content-Type": "text/html"}, **kwargs)


def test_live_acquisition_is_opt_in_and_requires_terms_review():
    def unexpected_request(_):
        pytest.fail("A disabled fetcher made an HTTP request")

    for enabled, terms_reviewed in ((False, False), (False, True), (True, False)):
        with SafeFetcher(
            {"www.xmu.edu.my"},
            enabled=enabled,
            terms_reviewed=terms_reviewed,
            transport=httpx.MockTransport(unexpected_request),
        ) as fetcher:
            with pytest.raises(FetchError, match="terms review") as error:
                fetcher.fetch_html(PAGE)
            assert error.value.code == "live_fetch_disabled"


def test_fetch_keeps_hash_time_url_and_cached_robots_with_rate_limit():
    requests = []
    body = "<html><h1>Synthetic undergraduate programme</h1></html>"

    def handler(request):
        requests.append(request)
        return robots_response() if request.url.path == "/robots.txt" else html_response(body)

    fetcher, clock = make_fetcher(handler)
    with fetcher:
        first = fetcher.fetch_html(PAGE)
        second = fetcher.fetch_html(f"{BASE}/accounting")
    assert [str(request.url) for request in requests] == [
        f"{BASE}/robots.txt",
        PAGE,
        f"{BASE}/accounting",
    ]
    assert first.url == PAGE
    assert first.html == body
    assert first.sha256 == hashlib.sha256(body.encode()).hexdigest() == second.sha256
    assert first.retrieved_at.utcoffset() == timedelta(0)
    assert clock.sleeps == [2.0, 2.0]
    assert all(request.headers["User-Agent"] == "SHIFTOS/0.2" for request in requests)
    assert all(request.headers["Accept-Encoding"] == "identity" for request in requests)
    assert all(request.extensions["shiftos_pinned_ip"] == PUBLIC_IP for request in requests)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.xmu.edu.my/courses",
        "https://evil.example/courses",
        "https://www.xmu.edu.my.evil.example/courses",
        "https://www.xmu.edu.my:443/courses",
        "https://name:password@www.xmu.edu.my/courses",
        "https://name@www.xmu.edu.my/courses",
        "https://127.0.0.1/courses",
        "https://[::1]/courses",
        "https://www.xmu.edu.my./courses",
        "https://www.xmu.edu.my/courses#fragment",
        "https://www.xmu.edu.my\\@evil.example/courses",
        "https://www.xmu.edu.my/\ncourses",
    ],
)
def test_disallowed_urls_never_reach_transport(url):
    def handler(_):
        pytest.fail("A disallowed URL reached HTTP")

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(url)
    assert error.value.code == "unsafe_source_url"
    assert url not in error.value.message


@pytest.mark.parametrize(
    "addresses",
    [
        ["127.0.0.1"],
        ["10.0.0.1"],
        ["169.254.169.254"],
        ["::1"],
        ["fc00::1"],
        ["fe80::1"],
        ["224.0.0.1"],
        ["not-an-ip"],
        [],
        [PUBLIC_IP, "192.168.0.1"],
    ],
)
def test_every_dns_address_must_be_public(addresses):
    def handler(_):
        pytest.fail("An unsafe DNS answer reached HTTP")

    fetcher, _ = make_fetcher(handler, resolver=lambda _: addresses)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "unsafe_source_url"


def test_dns_failure_is_sanitized():
    def resolver(_):
        raise OSError("internal resolver diagnostic with secret")

    fetcher, _ = make_fetcher(lambda _: html_response(), resolver=resolver)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert "secret" not in str(error.value)
    assert "secret" not in "".join(traceback.format_exception(error.value))
    assert error.value.code == "unsafe_source_url"


def test_production_transport_pins_ip_and_retains_host_and_tls_name(monkeypatch):
    captured = []

    class RecordingHTTPTransport:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False
            assert kwargs["retries"] == 0

        def handle_request(self, request):
            captured.append(request)
            return httpx.Response(200, content=b"ok")

        def close(self):
            pass

    monkeypatch.setattr(httpx, "HTTPTransport", RecordingHTTPTransport)
    with _PinnedHTTPTransport() as transport:
        transport.handle_request(
            httpx.Request("GET", PAGE, extensions={"shiftos_pinned_ip": PUBLIC_IP})
        )
    assert captured[0].url.host == PUBLIC_IP
    assert captured[0].url.scheme == "https"
    assert captured[0].headers["Host"] == "www.xmu.edu.my"
    assert captured[0].extensions["sni_hostname"] == "www.xmu.edu.my"
    assert captured[0].url.path == "/undergraduate-programmes"


@pytest.mark.parametrize("status", [401, 403, 500])
def test_unavailable_robots_fails_closed(status):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return robots_response(status=status)

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "robots_unavailable"
    assert set(paths) == {"/robots.txt"}
    assert len(paths) == (3 if status == 500 else 1)


def test_robots_404_default_deny_and_explicit_absent_policy():
    def handler(request):
        return robots_response(status=404) if request.url.path == "/robots.txt" else html_response()

    denied, _ = make_fetcher(handler)
    with denied, pytest.raises(FetchError) as error:
        denied.fetch_html(PAGE)
    assert error.value.code == "robots_unavailable"
    allowed, _ = make_fetcher(handler, absent_robots_policy="allow")
    with allowed:
        assert allowed.fetch_html(PAGE).html.startswith("<html>")


@pytest.mark.parametrize("text", ["", "<html>Access denied</html>", "captcha required", "\ufffd"])
def test_unrecognizable_robots_never_allows_source(text):
    fetcher, _ = make_fetcher(lambda _: robots_response(text))
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "robots_unavailable"


def test_robots_denial_prevents_page_request():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return robots_response()

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(f"{BASE}/private/plan")
    assert error.value.code == "robots_denied"
    assert paths == ["/robots.txt"]


def test_publisher_crawl_delay_is_observed():
    def handler(request):
        return (
            robots_response("User-agent: *\nCrawl-delay: 5\nDisallow:\n")
            if request.url.path == "/robots.txt"
            else html_response()
        )

    fetcher, clock = make_fetcher(handler)
    with fetcher:
        fetcher.fetch_html(PAGE)
    assert clock.sleeps == [5.0]


def test_long_publisher_delay_stops_instead_of_blocking_or_bypassing():
    fetcher, clock = make_fetcher(lambda _: robots_response("User-agent: *\nCrawl-delay: 120\n"))
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "publisher_backoff"
    assert clock.sleeps == []


def test_cross_host_redirect_checks_destination_robots_before_source():
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return robots_response()
        if request.url.host == "www.xmu.edu.my":
            return httpx.Response(302, headers={"Location": "https://xmu.edu.my/accounting"})
        return html_response()

    fetcher, _ = make_fetcher(handler)
    with fetcher:
        result = fetcher.fetch_html(PAGE)
    assert result.url == "https://xmu.edu.my/accounting"
    assert requests == [
        f"{BASE}/robots.txt",
        PAGE,
        "https://xmu.edu.my/robots.txt",
        "https://xmu.edu.my/accounting",
    ]


@pytest.mark.parametrize(
    "destination",
    ["https://127.0.0.1/secret", "https://evil.example/private", "http://www.xmu.edu.my/no-tls"],
)
def test_unsafe_redirect_is_not_requested(destination):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return robots_response()
        return httpx.Response(302, headers={"Location": destination})

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "unsafe_source_url"
    assert len(requests) == 2


def test_redirect_limit_is_bounded():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return robots_response()
        return httpx.Response(302, headers={"Location": "/loop"})

    fetcher, _ = make_fetcher(handler, max_redirects=2)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "redirect_limit"
    assert len(requests) == 4


def test_publisher_403_is_not_retried_and_body_is_not_exposed():
    requests = []

    def handler(request):
        requests.append(request)
        return (
            robots_response()
            if request.url.path == "/robots.txt"
            else httpx.Response(403, text="SECRET upstream body")
        )

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "access_denied"
    assert "SECRET" not in str(error.value)
    assert len(requests) == 2


@pytest.mark.parametrize(
    "content_type", ["application/pdf", "application/json", "application/octet-stream", ""]
)
def test_non_html_content_is_rejected(content_type):
    def handler(request):
        return (
            robots_response()
            if request.url.path == "/robots.txt"
            else httpx.Response(200, content=b"data", headers={"Content-Type": content_type})
        )

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "unsupported_format"


def test_pdf_extension_is_rejected_before_robots_or_page_request():
    def handler(_):
        pytest.fail("A binary extension should not be requested")

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(f"{BASE}/brochure.pdf")
    assert error.value.code == "unsupported_format"


@pytest.mark.parametrize("content_length", ["1000", None])
def test_response_size_is_bounded_with_or_without_length(content_length):
    def handler(request):
        if request.url.path == "/robots.txt":
            return robots_response()
        headers = {"Content-Type": "text/html"}
        if content_length:
            headers["Content-Length"] = content_length
        return httpx.Response(200, headers=headers, stream=httpx.ByteStream(b"x" * 1000))

    fetcher, _ = make_fetcher(handler, max_bytes=100)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "response_too_large"


def test_compressed_content_is_not_decompressed_before_size_check():
    def handler(request):
        if request.url.path == "/robots.txt":
            return robots_response()
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html", "Content-Encoding": "gzip"},
            stream=httpx.ByteStream(b"not decoded"),
        )

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "unsupported_encoding"


def test_transient_retries_are_bounded_and_observe_retry_after():
    attempts = 0

    def handler(request):
        nonlocal attempts
        if request.url.path == "/robots.txt":
            return robots_response()
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return html_response()

    fetcher, clock = make_fetcher(handler)
    with fetcher:
        fetcher.fetch_html(PAGE)
    assert attempts == 3
    assert clock.sleeps == [2.0, 3.0, 3.0]


def test_network_failure_stops_after_three_attempts():
    attempts = 0

    def handler(request):
        nonlocal attempts
        if request.url.path == "/robots.txt":
            return robots_response()
        attempts += 1
        raise httpx.ConnectError("SECRET network detail", request=request)

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "network_error"
    assert "SECRET" not in error.value.message
    assert "SECRET" not in "".join(traceback.format_exception(error.value))
    assert attempts == 3


@pytest.mark.parametrize(
    "retry_after", ["120", format_datetime(datetime.now(UTC) + timedelta(hours=1))]
)
def test_long_retry_after_requires_later_manual_retry(retry_after):
    def handler(request):
        return (
            robots_response()
            if request.url.path == "/robots.txt"
            else httpx.Response(503, headers={"Retry-After": retry_after})
        )

    fetcher, clock = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "publisher_backoff"
    assert clock.sleeps == [2.0]


def test_captcha_page_reports_access_challenge():
    def handler(request):
        return (
            robots_response()
            if request.url.path == "/robots.txt"
            else html_response("<html>Verify you are human</html>")
        )

    fetcher, _ = make_fetcher(handler)
    with fetcher, pytest.raises(FetchError) as error:
        fetcher.fetch_html(PAGE)
    assert error.value.code == "access_challenge"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_interval": 0},
        {"min_interval": float("nan")},
        {"min_interval": float("inf")},
        {"max_bytes": 10_000_000},
        {"max_bytes": 4.1},
        {"max_attempts": 4},
        {"max_redirects": 6},
        {"timeout": 60},
        {"timeout": float("nan")},
        {"absent_robots_policy": "guess"},
    ],
)
def test_unsafe_configuration_bounds_are_rejected(kwargs):
    with pytest.raises(ValueError):
        SafeFetcher({"www.xmu.edu.my"}, **kwargs)


def test_unreviewed_provider_host_cannot_be_enabled_by_configuration():
    with pytest.raises(ValueError, match="reviewed official"):
        SafeFetcher({"evil.example"}, enabled=True, terms_reviewed=True)
