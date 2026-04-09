from __future__ import annotations

import logging
from datetime import UTC, datetime

from newsr.domain import SectionCandidate
from newsr.providers.search.duckduckgo import DuckDuckGoSearchClient, SearchResult
from newsr.providers.topic.provider import TopicWatchProvider


class FakeSearchClient:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.calls: list[tuple[str, int]] = []

    def search(  # type: ignore[no-untyped-def]
        self,
        query: str,
        limit: int = 5,
        cancellation=None,
        *,
        log_request: bool = True,
    ) -> list[SearchResult]:
        self.calls.append((query, limit))
        return list(self._results)


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


def test_topic_provider_fetch_candidates_uses_normalized_url_ids(monkeypatch) -> None:
    provider = TopicWatchProvider(
        provider_id="topic:openai-policy",
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        search_client=FakeSearchClient(
            [
                SearchResult(title="One", url="https://example.com/a?utm=1", snippet="A"),
                SearchResult(title="Duplicate", url="https://example.com/a?utm=1", snippet="B"),
                SearchResult(title="Two", url="https://example.com/b", snippet="C"),
            ]
        ),
    )
    target = provider.default_targets()[0]

    candidates = provider.fetch_candidates(target, limit=2)

    assert [candidate.article_id for candidate in candidates] == [
        "web:https://example.com/a?utm=1",
        "web:https://example.com/b",
    ]
    assert [candidate.provider_id for candidate in candidates] == ["topic:openai-policy", "topic:openai-policy"]


def test_topic_provider_fetch_article_extracts_generic_web_content(monkeypatch) -> None:
    provider = TopicWatchProvider(
        provider_id="topic:openai-policy",
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        search_client=FakeSearchClient([]),
    )
    html = """
    <html>
      <head>
        <title>Fallback title</title>
        <meta property="og:title" content="OpenAI updates policy" />
        <meta property="og:url" content="https://example.com/policy" />
        <meta name="author" content="Reporter" />
        <meta property="article:published_time" content="2026-03-25T10:15:00Z" />
      </head>
      <body>
        <article>
          <p>This is a long enough first paragraph to be kept in the extracted article body for topic watch parsing.</p>
          <p>This is a second sufficiently detailed paragraph that should also appear in the extracted text output.</p>
        </article>
      </body>
    </html>
    """
    monkeypatch.setattr("newsr.providers.topic.provider._read_url", lambda url, cancellation=None: html)

    article = provider.fetch_article(
        SectionCandidate(
            article_id="web:https://example.com/policy",
            provider_id="topic:openai-policy",
            provider_article_id="https://example.com/policy",
            url="https://example.com/policy",
            category="topic",
        )
    )

    assert article.title == "OpenAI updates policy"
    assert article.url == "https://example.com/policy"
    assert article.author == "Reporter"
    assert article.published_at == datetime(2026, 3, 25, 10, 15, tzinfo=UTC)
    assert "first paragraph" in article.body
    assert "second sufficiently detailed paragraph" in article.body


def test_topic_provider_search_requests_do_not_emit_non_provider_network_logs(
    monkeypatch, caplog
) -> None:
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
        "newsr.providers.search.duckduckgo.urlopen",
        lambda req, timeout=30: FakeHTTPResponse(html, status=200),
    )
    provider = TopicWatchProvider(
        provider_id="topic:openai-policy",
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        search_client=DuckDuckGoSearchClient(),
    )
    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="newsr.llm"):
            provider.fetch_candidates(provider.default_targets()[0], limit=1)
    finally:
        logger.propagate = original_propagate

    assert not any("network_request_" in record.message for record in caplog.records)
