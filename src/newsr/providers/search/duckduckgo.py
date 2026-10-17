from __future__ import annotations

from dataclasses import dataclass
import http.client
import logging
from time import perf_counter
from typing import Callable
from urllib.parse import parse_qs, quote, quote_plus, unquote, urljoin, urlparse, urlunsplit

from bs4 import BeautifulSoup

from ...cancellation import RefreshCancellation, RefreshCancelled
from ...runtime_logging import configure_cache_logger
from .errors import SearchChallengeError, SearchCooldownError, SearchUnavailableError
from .throttle import SearchThrottle
from .transport import CurlBrowserTransport, SearchTransport

DUCKDUCKGO_HTML_ROOT = "https://html.duckduckgo.com/html/"
DUCKDUCKGO_LITE_ROOT = "https://lite.duckduckgo.com/lite/"
DUCKDUCKGO_ROOT = "https://duckduckgo.com"
LOGGER = logging.getLogger("newsr.llm")
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True, slots=True)
class _Endpoint:
    name: str
    url: str
    origin: str
    fields: tuple[tuple[str, str], ...]

    def form(self, query: str) -> dict[str, str]:
        return {"q": query, **dict(self.fields)}

    def headers(self) -> dict[str, str]:
        return {"Origin": self.origin, "Referer": f"{self.origin}/"}


_HTML_ENDPOINT = _Endpoint(
    name="html",
    url=DUCKDUCKGO_HTML_ROOT,
    origin="https://html.duckduckgo.com",
    fields=(("b", ""), ("kl", "")),
)
_LITE_ENDPOINT = _Endpoint(
    name="lite",
    url=DUCKDUCKGO_LITE_ROOT,
    origin="https://lite.duckduckgo.com",
    fields=(("kl", ""),),
)


class _ChallengePage(Exception):
    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


class DuckDuckGoSearchClient:
    def __init__(
        self,
        request_retries: int = 2,
        *,
        transport: SearchTransport | None = None,
        throttle: SearchThrottle | None = None,
        on_challenge: Callable[[str], None] | None = None,
    ) -> None:
        if request_retries < 0:
            raise ValueError("request_retries must be non-negative")
        self.request_retries = request_retries
        self._transport = transport or CurlBrowserTransport()
        self._throttle = throttle or SearchThrottle()
        self._on_challenge = on_challenge

    def search(
        self,
        query: str,
        limit: int = 5,
        cancellation: RefreshCancellation | None = None,
        *,
        log_request: bool = True,
        background: bool = False,
    ) -> list[SearchResult]:
        configure_cache_logger(LOGGER, filename="newsr-llm.log")
        cooling_down = self._throttle.cooldown_remaining() > 0
        try:
            html = self._read_endpoint(
                _HTML_ENDPOINT, query, cancellation, log_request=log_request, background=background
            )
        except _ChallengePage as exc:
            self._transport.reset()
            if cooling_down:
                raise self._challenge_error(query, exc.status) from None
            try:
                html = self._read_endpoint(
                    _LITE_ENDPOINT, query, cancellation, log_request=log_request, background=background
                )
            except _ChallengePage as exc:
                raise self._challenge_error(query, exc.status) from None
            results = parse_lite_results(html)
        else:
            results = parse_search_results(html)
        self._throttle.record_success()
        return results[:limit]

    def _read_endpoint(
        self,
        endpoint: _Endpoint,
        query: str,
        cancellation: RefreshCancellation | None,
        *,
        log_request: bool,
        background: bool,
    ) -> str:
        method = "POST"
        logged_query = quote_plus(query)
        max_attempts = self.request_retries + 1
        for attempt in range(1, max_attempts + 1):
            self._wait_turn(endpoint, logged_query, cancellation, background=background)
            started_at = perf_counter()
            try:
                response = self._transport.post(
                    endpoint.url,
                    endpoint.form(query),
                    headers=endpoint.headers(),
                    cancellation=cancellation,
                    timeout=30,
                )
            except RefreshCancelled:
                raise
            except (OSError, http.client.HTTPException) as exc:
                if cancellation is not None:
                    cancellation.raise_if_cancelled()
                if attempt < max_attempts:
                    if log_request:
                        LOGGER.warning(
                            "network_request_retry method=%s url=%s endpoint=%s query=%s attempt=%s "
                            "max_attempts=%s error_type=%s error=%s",
                            method,
                            endpoint.url,
                            endpoint.name,
                            logged_query,
                            attempt,
                            max_attempts,
                            type(exc).__name__,
                            exc,
                        )
                    continue
                if log_request:
                    LOGGER.exception(
                        "network_request_failed method=%s url=%s endpoint=%s query=%s duration_s=%.3f "
                        "error_type=%s error=%s",
                        method,
                        endpoint.url,
                        endpoint.name,
                        logged_query,
                        perf_counter() - started_at,
                        type(exc).__name__,
                        exc,
                    )
                raise
            except Exception as exc:
                if log_request:
                    LOGGER.exception(
                        "network_request_failed method=%s url=%s endpoint=%s query=%s duration_s=%.3f "
                        "error_type=%s error=%s",
                        method,
                        endpoint.url,
                        endpoint.name,
                        logged_query,
                        perf_counter() - started_at,
                        type(exc).__name__,
                        exc,
                    )
                raise
            if log_request:
                LOGGER.info(
                    "network_request_done method=%s url=%s endpoint=%s query=%s status=%s duration_s=%.3f",
                    method,
                    endpoint.url,
                    endpoint.name,
                    logged_query,
                    response.status,
                    perf_counter() - started_at,
                )
            if response.status == 202 or _is_challenge_page(response.text):
                LOGGER.warning(
                    "search_challenge method=%s url=%s endpoint=%s query=%s status=%s",
                    method,
                    endpoint.url,
                    endpoint.name,
                    logged_query,
                    response.status,
                )
                raise _ChallengePage(response.status)
            if response.status >= 400:
                if log_request:
                    LOGGER.warning(
                        "network_request_failed method=%s url=%s endpoint=%s query=%s status=%s "
                        "duration_s=%.3f",
                        method,
                        endpoint.url,
                        endpoint.name,
                        logged_query,
                        response.status,
                        perf_counter() - started_at,
                    )
                raise SearchUnavailableError(f"DuckDuckGo search failed with HTTP {response.status}.")
            return response.text
        raise RuntimeError("DuckDuckGo request failed without a captured transport error")

    def _wait_turn(
        self,
        endpoint: _Endpoint,
        logged_query: str,
        cancellation: RefreshCancellation | None,
        *,
        background: bool,
    ) -> None:
        try:
            self._throttle.wait_turn(cancellation, background=background)
        except SearchCooldownError as exc:
            LOGGER.warning(
                "search_cooldown_skip endpoint=%s query=%s remaining_s=%.0f",
                endpoint.name,
                logged_query,
                exc.remaining_seconds,
            )
            raise

    def _challenge_error(self, query: str, status: int) -> SearchChallengeError:
        cooldown_seconds = self._throttle.record_challenge()
        browser_url = f"{DUCKDUCKGO_ROOT}/?q={quote_plus(query)}"
        LOGGER.warning(
            "search_cooldown_started query=%s cooldown_s=%.0f",
            quote_plus(query),
            cooldown_seconds,
        )
        if self._on_challenge is not None:
            try:
                self._on_challenge(browser_url)
            except Exception:
                LOGGER.exception("search_challenge_callback_failed url=%s", browser_url)
        return SearchChallengeError(
            "DuckDuckGo search is unavailable because DuckDuckGo returned an anti-bot challenge"
            f" page (HTTP {status}). Open DuckDuckGo in a browser to pass its check, then retry.",
            browser_url=browser_url,
        )


def parse_search_results(html: str) -> list[SearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []
    for node in soup.select(".result"):
        link = node.select_one(".result__title a[href], a.result__a[href]")
        if link is None:
            continue
        title = link.get_text(" ", strip=True)
        url = normalize_result_url(str(link.get("href", "")).strip())
        if not title or not url:
            continue
        snippet_node = node.select_one(".result__snippet")
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node is not None else ""
        results.append(SearchResult(title=title, url=url, snippet=snippet))
    return results


def parse_lite_results(html: str) -> list[SearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []
    current: SearchResult | None = None
    for row in soup.select("tr"):
        link = row.select_one("a.result-link[href]")
        if link is not None:
            current = None
            if "result-sponsored" in (row.get("class") or []):
                continue
            title = link.get_text(" ", strip=True)
            url = normalize_result_url(str(link.get("href", "")).strip())
            if not title or not url or _is_ad_url(url):
                continue
            current = SearchResult(title=title, url=url, snippet="")
            results.append(current)
            continue
        snippet_node = row.select_one("td.result-snippet")
        if snippet_node is not None and current is not None and not current.snippet:
            current.snippet = snippet_node.get_text(" ", strip=True)
    return results


def normalize_result_url(url: str) -> str:
    if not url:
        return ""
    resolved = urljoin(DUCKDUCKGO_ROOT, url)
    parsed = urlparse(resolved)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        if target:
            return normalize_result_url(unquote(target))
    hostname = parsed.hostname.encode("idna").decode("ascii") if parsed.hostname is not None else ""
    port = f":{parsed.port}" if parsed.port is not None else ""
    auth = ""
    if parsed.username is not None:
        auth = quote(parsed.username, safe="")
        if parsed.password is not None:
            auth += f":{quote(parsed.password, safe='')}"
        auth += "@"
    netloc = f"{auth}{hostname}{port}" if hostname else parsed.netloc
    path = quote(parsed.path, safe="/%:@!$&'()*+,;=-._~")
    query = quote(parsed.query, safe="=&%/:?@!$'()*+,;~-._")
    fragment = quote(parsed.fragment, safe="%/:?@!$&'()*+,;=-._~")
    return urlunsplit((parsed.scheme, netloc, path, query, fragment))


def _is_ad_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/y.js"


def _is_challenge_page(payload: str) -> bool:
    lowered = payload.lower()
    markers = (
        "bots use duckduckgo too",
        "anomaly-modal",
        "challenge-form",
        "anomaly.js?",
        "error-lite@duckduckgo.com",
    )
    return any(marker in lowered for marker in markers)
