from __future__ import annotations

from datetime import UTC, datetime

from bs4 import BeautifulSoup

from ...cancellation import RefreshCancellation
from ...domain import ArticleContent, ProviderTarget, SectionCandidate
from ..search.duckduckgo import DuckDuckGoSearchClient, normalize_result_url
from ..transport import browser_headers, read_text_url


class TopicWatchProvider:
    def __init__(
        self,
        *,
        provider_id: str,
        display_name: str,
        topic_query: str,
        search_client: DuckDuckGoSearchClient,
    ) -> None:
        self.provider_id = provider_id
        self.display_name = display_name
        self._topic_query = topic_query
        self._search_client = search_client

    def default_targets(self) -> list[ProviderTarget]:
        return [self._build_target()]

    def discover_targets(
        self, cancellation: RefreshCancellation | None = None
    ) -> list[ProviderTarget]:
        return self.default_targets()

    def fetch_candidates(
        self,
        target: ProviderTarget,
        limit: int,
        cancellation: RefreshCancellation | None = None,
    ) -> list[SectionCandidate]:
        query = target.payload.get("query", self._topic_query).strip()
        seen_urls: set[str] = set()
        candidates: list[SectionCandidate] = []
        for result in self._search_client.search(
            query,
            limit=limit * 2,
            cancellation=cancellation,
            log_request=False,
        ):
            normalized_url = normalize_result_url(result.url)
            if not normalized_url or normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            candidates.append(
                SectionCandidate(
                    article_id=_article_id_for_url(normalized_url),
                    provider_id=self.provider_id,
                    provider_article_id=normalized_url,
                    url=normalized_url,
                    category="topic",
                )
            )
            if len(candidates) >= limit:
                break
        return candidates

    def fetch_article(
        self,
        candidate: SectionCandidate,
        cancellation: RefreshCancellation | None = None,
    ) -> ArticleContent:
        html = _read_url(candidate.url, cancellation)
        parsed = _parse_article_html(html, fallback_url=candidate.url)
        return ArticleContent(
            article_id=candidate.article_id,
            provider_id=candidate.provider_id,
            provider_article_id=candidate.provider_article_id,
            url=parsed.url,
            category=candidate.category,
            title=parsed.title,
            author=parsed.author,
            published_at=parsed.published_at,
            body=parsed.body,
        )

    def _build_target(self) -> ProviderTarget:
        return ProviderTarget(
            provider_id=self.provider_id,
            target_key="watch",
            target_kind="topic",
            label=self.display_name,
            payload={"query": self._topic_query},
            selected=True,
        )


class ParsedTopicArticle:
    def __init__(
        self,
        *,
        url: str,
        title: str,
        author: str | None,
        published_at: datetime | None,
        body: str,
    ) -> None:
        self.url = url
        self.title = title
        self.author = author
        self.published_at = published_at
        self.body = body


def _article_id_for_url(url: str) -> str:
    return f"web:{normalize_result_url(url)}"


def _read_url(url: str, cancellation: RefreshCancellation | None = None) -> str:
    return read_text_url(
        url,
        cancellation,
        headers=browser_headers(),
        errors="replace",
    )


def _parse_article_html(html: str, *, fallback_url: str) -> ParsedTopicArticle:
    soup = BeautifulSoup(html, "html.parser")
    title = _first_content(
        soup,
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
        "title",
    )
    body = _extract_body_text(soup)
    if len(body.strip()) < 200:
        raise ValueError("topic search result did not expose enough readable article text")
    canonical_url = _first_content(
        soup,
        'meta[property="og:url"]',
        'link[rel="canonical"]',
    )
    author = _first_content(
        soup,
        'meta[name="author"]',
        'meta[property="article:author"]',
    )
    published_at = _parse_published_at(
        _first_content(
            soup,
            'meta[property="article:published_time"]',
            'meta[name="pubdate"]',
            "time[datetime]",
        )
    )
    return ParsedTopicArticle(
        url=normalize_result_url(canonical_url or fallback_url),
        title=(title or fallback_url).strip(),
        author=author.strip() if author else None,
        published_at=published_at,
        body=body,
    )


def _first_content(soup: BeautifulSoup, *selectors: str) -> str:
    for selector in selectors:
        node = soup.select_one(selector)
        if node is None:
            continue
        for attribute in ("content", "href", "datetime"):
            value = node.get(attribute)
            if isinstance(value, str) and value.strip():
                return value.strip()
        text = node.get_text(" ", strip=True)
        if text:
            return text
    return ""


def _extract_body_text(soup: BeautifulSoup) -> str:
    containers = list(soup.select("article")) or list(soup.select("main")) or [soup.body or soup]
    paragraphs: list[str] = []
    for container in containers:
        for paragraph in container.select("p"):
            text = paragraph.get_text(" ", strip=True)
            if len(text) < 40:
                continue
            paragraphs.append(text)
        if paragraphs:
            break
    if not paragraphs:
        return ""
    return "\n\n".join(dict.fromkeys(paragraphs))


def _parse_published_at(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
