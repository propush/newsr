from __future__ import annotations

from dataclasses import dataclass
import logging
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, quote_plus, unquote, urljoin, urlparse, urlunsplit

from bs4 import BeautifulSoup

from ...cancellation import RefreshCancellation
from ...runtime_logging import configure_cache_logger
from ..transport import browser_headers, build_request, open_request, read_text_response

DUCKDUCKGO_HTML_ROOT = "https://html.duckduckgo.com/html/"
DUCKDUCKGO_ROOT = "https://duckduckgo.com"
LOGGER = logging.getLogger("newsr.llm")
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


class SearchUnavailableError(RuntimeError):
    """Raised when the upstream search provider returns no usable results page."""


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class DuckDuckGoSearchClient:
    def search(
        self,
        query: str,
        limit: int = 5,
        cancellation: RefreshCancellation | None = None,
        *,
        log_request: bool = True,
    ) -> list[SearchResult]:
        html = self._read_url(query, cancellation, log_request=log_request)
        return parse_search_results(html)[:limit]

    @staticmethod
    def _read_url(
        query: str,
        cancellation: RefreshCancellation | None = None,
        *,
        log_request: bool = True,
    ) -> str:
        req = build_request(
            f"{DUCKDUCKGO_HTML_ROOT}?q={quote_plus(query)}",
            headers=browser_headers(),
        )
        configure_cache_logger(LOGGER, filename="newsr-llm.log")
        if not log_request:
            with open_request(req, cancellation, timeout=30) as response:
                return read_text_response(response, cancellation)
        method = req.get_method()
        url = req.full_url
        started_at = perf_counter()
        try:
            with open_request(req, cancellation, timeout=30) as response:
                status = getattr(response, "status", "unknown")
                payload = read_text_response(response, cancellation)
                LOGGER.info(
                    "network_request_done method=%s url=%s status=%s duration_s=%.3f",
                    method,
                    url,
                    status,
                    perf_counter() - started_at,
                )
                _raise_if_search_page_unavailable(status, payload)
                return payload
        except HTTPError as exc:
            LOGGER.warning(
                "network_request_failed method=%s url=%s status=%s duration_s=%.3f error=%s",
                method,
                url,
                exc.code,
                perf_counter() - started_at,
                exc,
            )
            raise
        except Exception as exc:
            LOGGER.exception(
                "network_request_failed method=%s url=%s duration_s=%.3f error_type=%s error=%s",
                method,
                url,
                perf_counter() - started_at,
                type(exc).__name__,
                exc,
            )
            raise


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


def _raise_if_search_page_unavailable(status: object, payload: str) -> None:
    if not _is_challenge_page(payload):
        return
    status_text = str(status)
    raise SearchUnavailableError(
        "DuckDuckGo search is unavailable because DuckDuckGo returned an anti-bot challenge"
        f" page (HTTP {status_text})."
    )


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
