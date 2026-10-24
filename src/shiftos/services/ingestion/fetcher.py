"""Small, opt-in HTTP boundary for reviewed official curriculum providers.

No request is made until both live access and a terms review are enabled. A
missing robots.txt (404) blocks by default; an operator may explicitly select
``absent_robots_policy="allow"`` after reviewing the publisher's access policy.
Unreadable robots, denial responses and anti-bot pages never grant access.

Production connections use the vetted public IP directly, with the original
hostname preserved for Host and TLS certificate/SNI checks. This avoids a second
hostname resolution between the SSRF check and connection. Injected transports
are intended for offline tests and do not perform real connections.
"""

from __future__ import annotations

import hashlib
import ipaddress
import math
import socket
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

OFFICIAL_HOSTS = frozenset({"xmu.edu.my", "www.xmu.edu.my"})
USER_AGENT = "SHIFTOS/0.2"
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
_ROBOTS_TYPES = frozenset({"text/plain", "text/html"})


class FetchError(Exception):
    """Stable public error; never includes upstream response text or URLs."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FetchedPage:
    url: str
    html: str
    sha256: str
    retrieved_at: datetime


def _system_resolver(host: str) -> list[str]:
    return list({record[4][0] for record in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})


class _PinnedHTTPTransport(httpx.BaseTransport):
    """Connect to a checked IP without changing HTTPS hostname verification."""

    def __init__(self) -> None:
        self._transport = httpx.HTTPTransport(
            retries=0,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
            trust_env=False,
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        address = request.extensions["shiftos_pinned_ip"]
        hostname = request.url.host
        headers = request.headers.copy()
        headers["Host"] = hostname
        extensions = {**request.extensions, "sni_hostname": hostname}
        pinned = httpx.Request(
            request.method,
            request.url.copy_with(host=address),
            headers=headers,
            stream=request.stream,
            extensions=extensions,
        )
        return self._transport.handle_request(pinned)

    def close(self) -> None:
        self._transport.close()


class SafeFetcher:
    """Synchronous, one-worker fetcher; use a separate instance per worker.

    Bounds are ceilings, not targets. Rate limiting also applies to robots,
    retries and redirects. Robots rules are cached only for this short-lived
    instance. Policy/fetch errors should be surfaced with the manual-import
    fallback; callers must not retry by disabling protections.
    """

    reviewed_hosts = OFFICIAL_HOSTS
    accepted_suffixes = frozenset({".html", ".htm", ".php", ".aspx"})
    accepted_types = _HTML_TYPES

    def __init__(
        self,
        allowed_hosts: Iterable[str],
        *,
        enabled: bool = False,
        terms_reviewed: bool = False,
        transport: httpx.BaseTransport | None = None,
        resolver: Callable[[str], Iterable[str]] = _system_resolver,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        min_interval: float = 2.0,
        max_bytes: int = 2_000_000,
        max_redirects: int = 3,
        max_attempts: int = 3,
        timeout: float = 20.0,
        absent_robots_policy: str = "deny",
    ) -> None:
        self.allowed_hosts = frozenset(allowed_hosts)
        if not self.allowed_hosts or not self.allowed_hosts <= self.reviewed_hosts:
            raise ValueError("Only explicitly reviewed official provider hosts are supported")
        if (
            not math.isfinite(min_interval)
            or min_interval < 2
            or not isinstance(max_bytes, int)
            or not 1 <= max_bytes <= 5_000_000
        ):
            raise ValueError("Invalid request interval or response-size bound")
        if (
            not isinstance(max_redirects, int)
            or not isinstance(max_attempts, int)
            or not 0 <= max_redirects <= 5
            or not 1 <= max_attempts <= 3
            or not math.isfinite(timeout)
            or not 0 < timeout <= 20
        ):
            raise ValueError("Invalid redirect, attempt or timeout bound")
        if absent_robots_policy not in {"allow", "deny"}:
            raise ValueError("Absent robots policy must be allow or deny")
        self.enabled = enabled
        self.terms_reviewed = terms_reviewed
        self._resolver = resolver
        self._sleep = sleep
        self._monotonic = monotonic
        self._min_interval = min_interval
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects
        self._max_attempts = max_attempts
        self._absent_robots_policy = absent_robots_policy
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self._client = httpx.Client(
            transport=transport if transport is not None else _PinnedHTTPTransport(),
            timeout=httpx.Timeout(timeout),
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
        )

    def __enter__(self) -> SafeFetcher:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def fetch_html(self, url: str) -> FetchedPage:
        if not self.enabled or not self.terms_reviewed:
            raise FetchError(
                "live_fetch_disabled",
                "Live acquisition requires configured access and a recorded terms review; "
                "use structured manual import.",
            )
        final_url, content, encoding = self._request(url, robots=False)
        try:
            html = content.decode(encoding or "utf-8", errors="strict")
        except (LookupError, UnicodeError):
            raise FetchError(
                "unreadable_content", "The official page could not be decoded."
            ) from None
        if any(
            marker in html.casefold()
            for marker in ("cf-chl-", "g-recaptcha", "hcaptcha", "verify you are human")
        ):
            raise FetchError(
                "access_challenge", "The publisher requires an access check; use manual import."
            )
        return FetchedPage(
            url=final_url,
            html=html,
            sha256=hashlib.sha256(content).hexdigest(),
            retrieved_at=datetime.now(UTC),
        )

    def _validate_url(self, url: str) -> tuple[str, str]:
        try:
            parsed = urlsplit(url)
            host = parsed.hostname
            if (
                parsed.scheme != "https"
                or host not in self.allowed_hosts
                or parsed.username is not None
                or parsed.password is not None
                or parsed.port is not None
                or parsed.fragment
                or "\\" in url
                or any(ord(character) < 32 for character in url)
            ):
                raise ValueError
            addresses = list(self._resolver(host))
            if not addresses:
                raise ValueError
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if not ip.is_global or ip.is_multicast or "%" in address:
                    raise ValueError
            return host, addresses[0]
        except (ValueError, OSError, TypeError):
            raise FetchError(
                "unsafe_source_url", "The source URL or network destination is not permitted."
            ) from None

    def _wait_for_host(self, host: str) -> None:
        if self._min_interval > 30:
            raise FetchError(
                "publisher_backoff", "The publisher requires a longer pause; retry manually later."
            )
        previous = self._last_request.get(host)
        if previous is not None:
            delay = self._min_interval - (self._monotonic() - previous)
            if delay > 0:
                self._sleep(delay)
        self._last_request[host] = self._monotonic()

    def _ensure_robots(self, url: str) -> None:
        host, _ = self._validate_url(url)
        if host not in self._robots:
            try:
                _, content, _ = self._request(f"https://{host}/robots.txt", robots=True)
                text = content.decode("utf-8-sig", errors="strict")
                if "<html" in text.casefold() or "<!doctype" in text.casefold():
                    raise ValueError
                # A successful but unrecognisable/empty body is not an allow rule.
                if not any(
                    line.strip().lower().startswith("user-agent:") for line in text.splitlines()
                ):
                    raise ValueError
                parser = RobotFileParser()
                parser.parse(text.splitlines())
                self._robots[host] = parser
            except FetchError as exc:
                if exc.code == "robots_absent" and self._absent_robots_policy == "allow":
                    self._robots[host] = None
                else:
                    raise FetchError(
                        "robots_unavailable",
                        "Robots policy is unavailable or restrictive; use manual import.",
                    ) from exc
            except (UnicodeError, ValueError):
                raise FetchError(
                    "robots_unavailable", "Robots policy could not be read; use manual import."
                ) from None
        parser = self._robots[host]
        if parser is not None:
            if not parser.can_fetch(USER_AGENT, url):
                raise FetchError("robots_denied", "Robots policy disallows this source.")
            crawl_delay = parser.crawl_delay(USER_AGENT)
            request_rate = parser.request_rate(USER_AGENT)
            if crawl_delay is not None:
                self._min_interval = max(self._min_interval, float(crawl_delay))
            if request_rate is not None and request_rate.requests > 0:
                self._min_interval = max(
                    self._min_interval, request_rate.seconds / request_rate.requests
                )

    def _request(self, url: str, *, robots: bool) -> tuple[str, bytes, str | None]:
        current_url = url
        for redirect in range(self._max_redirects + 1):
            host, address = self._validate_url(current_url)
            if not robots:
                suffix = PurePosixPath(urlsplit(current_url).path).suffix.casefold()
                if suffix and suffix not in self.accepted_suffixes:
                    raise FetchError(
                        "unsupported_format", "Only official HTML source pages are supported."
                    )
                self._ensure_robots(current_url)
            for attempt in range(self._max_attempts):
                self._wait_for_host(host)
                try:
                    with self._client.stream(
                        "GET", current_url, extensions={"shiftos_pinned_ip": address}
                    ) as response:
                        status = response.status_code
                        if status in _REDIRECT_STATUSES:
                            location = response.headers.get("location")
                            if not location or redirect == self._max_redirects:
                                raise FetchError(
                                    "redirect_limit", "The source redirect limit was reached."
                                )
                            current_url = urljoin(current_url, location)
                            self._validate_url(current_url)
                            break
                        if status in {401, 403}:
                            raise FetchError(
                                "access_denied", "The publisher denied access; use manual import."
                            )
                        if status == 404 and robots:
                            raise FetchError("robots_absent", "The publisher has no robots file.")
                        if status in _RETRY_STATUSES and attempt + 1 < self._max_attempts:
                            self._sleep(self._retry_delay(response, attempt))
                            continue
                        if status != 200:
                            raise FetchError(
                                "source_unavailable",
                                "The official source is currently unavailable.",
                            )
                        media_type = (
                            response.headers.get("content-type", "")
                            .split(";", 1)[0]
                            .strip()
                            .lower()
                        )
                        accepted_types = _ROBOTS_TYPES if robots else self.accepted_types
                        if media_type not in accepted_types:
                            raise FetchError(
                                "unsupported_format",
                                "The source returned an unsupported content type.",
                            )
                        if (
                            response.headers.get("content-encoding", "identity").lower()
                            != "identity"
                        ):
                            raise FetchError(
                                "unsupported_encoding",
                                "The source returned unsupported compression.",
                            )
                        limit = min(self._max_bytes, 128_000) if robots else self._max_bytes
                        content_length = response.headers.get("content-length")
                        if content_length is not None:
                            try:
                                if int(content_length) < 0 or int(content_length) > limit:
                                    raise FetchError(
                                        "response_too_large",
                                        "The source exceeds the permitted size.",
                                    )
                            except ValueError:
                                raise FetchError(
                                    "invalid_response",
                                    "The source returned invalid response metadata.",
                                ) from None
                        content = bytearray()
                        for chunk in response.iter_bytes(chunk_size=min(65_536, limit + 1)):
                            if len(content) + len(chunk) > limit:
                                raise FetchError(
                                    "response_too_large", "The source exceeds the permitted size."
                                )
                            content.extend(chunk)
                        return current_url, bytes(content), response.charset_encoding
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt + 1 == self._max_attempts:
                        raise FetchError(
                            "network_error",
                            "The official source could not be reached; use manual import.",
                        ) from None
                    self._sleep(min(2**attempt, 4))
                except httpx.HTTPError:
                    raise FetchError(
                        "network_error", "The official source request failed."
                    ) from None
            else:
                raise FetchError(
                    "source_unavailable", "The official source is currently unavailable."
                )
        raise FetchError("redirect_limit", "The source redirect limit was reached.")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("retry-after")
        if value:
            try:
                delay = float(value)
                if not math.isfinite(delay):
                    delay = 2**attempt
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(value)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=UTC)
                    delay = (parsed - datetime.now(UTC)).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    delay = 2**attempt
            # Do not retry sooner than requested; long waits require manual resumption.
            if delay > 30:
                raise FetchError(
                    "publisher_backoff",
                    "The publisher requested a longer pause; retry manually later.",
                )
            return max(0, delay)
        return min(2**attempt, 4)
