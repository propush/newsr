from __future__ import annotations

import logging
from urllib.error import HTTPError

import pytest

from newsr.providers.search import DuckDuckGoSearchClient, parse_search_results
from newsr.providers.search.duckduckgo import SearchUnavailableError


class FakeHTTPResponse:
    def __init__(self, body: str, *, status: int = 200) -> None:
        self.status = status
        self._body = body.encode("utf-8")

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            data = self._body
            self._body = b""
            return data
        if not self._body:
            return b""
        data = self._body[:size]
        self._body = self._body[size:]
        return data

    def close(self) -> None:
        return None


def test_parse_search_results_extracts_title_url_and_snippet() -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="https://example.com/story">Example Story</a>
          </h2>
          <a class="result__snippet">Useful background context.</a>
        </div>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="https://example.com/second">Second Story</a>
          </h2>
          <div class="result__snippet">Another snippet.</div>
        </div>
      </body>
    </html>
    """

    results = parse_search_results(html)

    assert results == [
        (
            results[0].__class__(
                title="Example Story",
                url="https://example.com/story",
                snippet="Useful background context.",
            )
        ),
        (
            results[1].__class__(
                title="Second Story",
                url="https://example.com/second",
                snippet="Another snippet.",
            )
        ),
    ]


def test_parse_search_results_unwraps_duckduckgo_redirect_links() -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.bafta.org%2Fawards%2Fgames">BAFTA Games Awards</a>
          </h2>
          <div class="result__snippet">Awards page.</div>
        </div>
      </body>
    </html>
    """

    results = parse_search_results(html)

    assert results == [
        results[0].__class__(
            title="BAFTA Games Awards",
            url="https://www.bafta.org/awards/games",
            snippet="Awards page.",
        )
    ]


def test_parse_search_results_normalizes_protocol_relative_links() -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="//example.com/story">Example Story</a>
          </h2>
          <div class="result__snippet">Useful background context.</div>
        </div>
      </body>
    </html>
    """

    results = parse_search_results(html)

    assert results == [
        results[0].__class__(
            title="Example Story",
            url="https://example.com/story",
            snippet="Useful background context.",
        )
    ]


def test_parse_search_results_escapes_non_latin_characters_in_target_url() -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2F%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8%2F%D0%B8%D0%B3%D1%80%D1%8B%3F%D1%82%D0%B5%D0%BC%D0%B0%3D%D0%91%D0%90%D0%A4%D0%A2%D0%90">BAFTA Games Awards</a>
          </h2>
          <div class="result__snippet">Awards page.</div>
        </div>
      </body>
    </html>
    """

    results = parse_search_results(html)

    assert results == [
        results[0].__class__(
            title="BAFTA Games Awards",
            url="https://example.com/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8/%D0%B8%D0%B3%D1%80%D1%8B?%D1%82%D0%B5%D0%BC%D0%B0=%D0%91%D0%90%D0%A4%D0%A2%D0%90",
            snippet="Awards page.",
        )
    ]


def test_search_logs_request_metadata_without_logging_response_body(monkeypatch, caplog) -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="https://example.com/story">Example Story</a>
          </h2>
          <div class="result__snippet">Useful background context.</div>
        </div>
      </body>
    </html>
    """

    monkeypatch.setattr(
        "newsr.providers.search.duckduckgo.open_request",
        lambda req, cancellation=None, timeout=30: FakeHTTPResponse(html, status=200),
    )
    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="newsr.llm"):
            results = DuckDuckGoSearchClient().search("example query")
    finally:
        logger.propagate = original_propagate

    assert len(results) == 1
    assert any(
        "network_request_done" in record.message
        and "method=GET" in record.message
        and "url=https://html.duckduckgo.com/html/?q=example+query" in record.message
        and "status=200" in record.message
        for record in caplog.records
    )
    log_text = "\n".join(record.message for record in caplog.records)
    assert "Example Story" not in log_text
    assert "Useful background context." not in log_text
    assert "<html>" not in log_text


def test_search_raises_when_duckduckgo_returns_challenge_page(monkeypatch, caplog) -> None:
    html = """
    <html>
      <body>
        <form id="challenge-form">
          <div class="anomaly-modal__title">Unfortunately, bots use DuckDuckGo too.</div>
        </form>
      </body>
    </html>
    """

    monkeypatch.setattr(
        "newsr.providers.search.duckduckgo.open_request",
        lambda req, cancellation=None, timeout=30: FakeHTTPResponse(html, status=202),
    )
    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="newsr.llm"):
            with pytest.raises(SearchUnavailableError, match="anti-bot challenge"):
                DuckDuckGoSearchClient().search("example query")
    finally:
        logger.propagate = original_propagate

    assert any(
        "network_request_done" in record.message
        and "url=https://html.duckduckgo.com/html/?q=example+query" in record.message
        and "status=202" in record.message
        for record in caplog.records
    )


def test_search_raises_when_duckduckgo_returns_challenge_body_with_200(monkeypatch) -> None:
    html = """
    <html>
      <body>
        <div class="anomaly-modal__description">Please complete the following challenge.</div>
      </body>
    </html>
    """

    monkeypatch.setattr(
        "newsr.providers.search.duckduckgo.open_request",
        lambda req, cancellation=None, timeout=30: FakeHTTPResponse(html, status=200),
    )

    with pytest.raises(SearchUnavailableError, match="HTTP 200"):
        DuckDuckGoSearchClient().search("example query")


def test_search_logs_http_errors_without_logging_error_body(monkeypatch, caplog) -> None:
    def fail(req, cancellation=None, timeout=30):
        raise HTTPError(req.full_url, 503, "service unavailable", hdrs=None, fp=None)

    monkeypatch.setattr("newsr.providers.search.duckduckgo.open_request", fail)
    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True
    try:
        with caplog.at_level(logging.WARNING, logger="newsr.llm"):
            with pytest.raises(HTTPError):
                DuckDuckGoSearchClient().search("error query")
    finally:
        logger.propagate = original_propagate

    assert any(
        "network_request_failed" in record.message
        and "method=GET" in record.message
        and "url=https://html.duckduckgo.com/html/?q=error+query" in record.message
        and "status=503" in record.message
        for record in caplog.records
    )
    log_text = "\n".join(record.message for record in caplog.records)
    assert "<html>" not in log_text
