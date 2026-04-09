from __future__ import annotations

from dataclasses import dataclass
import logging
from time import perf_counter
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, quote_plus, unquote, urljoin, urlparse, urlunsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from ...cancellation import RefreshCancellation, cancellable_read
from ...runtime_logging import configure_cache_logger

DUCKDUCKGO_HTML_ROOT = "https://html.duckduckgo.com/html/"
DUCKDUCKGO_ROOT = "https://duckduckgo.com"
LOGGER = logging.getLogger("newsr.llm")
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


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
        req = Request(
            f"{DUCKDUCKGO_HTML_ROOT}?q={quote_plus(query)}",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0 Safari/537.36 newsr/0.1"
                )
            },
        )
        configure_cache_logger(LOGGER, filename="newsr-llm.log")
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        if not log_request:
            with urlopen(req, timeout=30) as response:
                return cancellable_read(response, cancellation).decode("utf-8")
        method = req.get_method()
        url = req.full_url
        started_at = perf_counter()
        try:
            with urlopen(req, timeout=30) as response:
                payload = cancellable_read(response, cancellation).decode("utf-8")
                LOGGER.info(
                    "network_request_done method=%s url=%s status=%s duration_s=%.3f",
                    method,
                    url,
                    getattr(response, "status", "unknown"),
                    perf_counter() - started_at,
                )
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
