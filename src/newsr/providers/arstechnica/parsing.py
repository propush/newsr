from __future__ import annotations

import json
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

_BODY_TAGS = ("p", "h2", "h3", "h4", "li", "blockquote", "pre")
_REMOVABLE_TAGS = {
    "aside",
    "button",
    "figure",
    "form",
    "iframe",
    "img",
    "noscript",
    "picture",
    "script",
    "style",
    "svg",
    "video",
}
_SKIP_CLASS_TOKENS = {
    "ad",
    "ads",
    "caption",
    "comment",
    "interlude",
    "newsletter",
    "promo",
    "related",
    "share",
    "sidebar",
    "social",
    "sponsored",
    "subscribe",
}
_SKIP_TEXT_SNIPPETS = (
    "discover all the benefits",
    "follow ars on",
    "newsletter",
    "read our affiliate link policy",
    "share this story",
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for article in _article_nodes(soup):
        article_url = _article_url_from_card(article)
        if article_url is None:
            continue
        article_id = article_id_from_url(article_url)
        if article_id in seen:
            continue
        seen.add(article_id)
        candidates.append(
            SectionCandidate(
                article_id=article_id,
                provider_id="arstechnica",
                provider_article_id=article_id,
                url=article_url,
                category=category,
            )
        )
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    metadata = _article_metadata(soup)
    title = _title_text(soup, metadata)
    author = _author_text(soup, metadata)
    published_at = _published_at(soup, metadata)
    url = _canonical_url(soup) or candidate.url
    body = _extract_body(soup, title)
    return ArticleContent(
        article_id=candidate.article_id,
        provider_id=candidate.provider_id,
        provider_article_id=candidate.provider_article_id,
        url=url,
        category=candidate.category,
        title=title or candidate.provider_article_id,
        author=author,
        published_at=published_at,
        body=body,
    )


def _article_nodes(soup: BeautifulSoup) -> list[Tag]:
    main = soup.select_one("main")
    if isinstance(main, Tag):
        nodes = [node for node in main.select("article") if isinstance(node, Tag)]
        if nodes:
            return nodes
    return [node for node in soup.select("article") if isinstance(node, Tag)]


def _article_url_from_card(article: Tag) -> str | None:
    for link in article.select("h1 a[href], h2 a[href], h3 a[href], a[href]"):
        href = str(link.get("href", "")).strip()
        if not href:
            continue
        url = normalize_url(href)
        if is_article_url(url):
            return url
    return None


def _title_text(soup: BeautifulSoup, metadata: dict[str, object]) -> str | None:
    headline = metadata.get("headline")
    if isinstance(headline, str) and headline.strip():
        return headline.strip()
    meta_title = _meta_content(soup, "property", "og:title")
    if meta_title:
        return meta_title
    heading = soup.select_one("h1")
    if isinstance(heading, Tag):
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    return None


def _author_text(soup: BeautifulSoup, metadata: dict[str, object]) -> str | None:
    author = metadata.get("author")
    if isinstance(author, dict):
        name = author.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    if isinstance(author, list):
        names = [
            name.strip()
            for item in author
            if isinstance(item, dict)
            for name in [item.get("name")]
            if isinstance(name, str) and name.strip()
        ]
        if names:
            return ", ".join(names)
    author_link = soup.select_one('a[href*="/author/"]')
    if isinstance(author_link, Tag):
        text = author_link.get_text(" ", strip=True)
        if text:
            return text
    return _meta_content(soup, "name", "author")


def _published_at(soup: BeautifulSoup, metadata: dict[str, object]) -> datetime | None:
    published_raw = metadata.get("datePublished")
    if isinstance(published_raw, str) and published_raw.strip():
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
    meta_published = _meta_content(soup, "property", "article:published_time")
    if meta_published:
        return datetime.fromisoformat(meta_published.replace("Z", "+00:00"))
    time_node = soup.select_one("time[datetime]")
    if not isinstance(time_node, Tag):
        return None
    raw = str(time_node.get("datetime", "")).strip()
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _canonical_url(soup: BeautifulSoup) -> str | None:
    link = soup.find("link", rel="canonical")
    if isinstance(link, Tag):
        href = str(link.get("href", "")).strip()
        if href:
            return normalize_url(href)
    meta_url = _meta_content(soup, "property", "og:url")
    if meta_url:
        return normalize_url(meta_url)
    return None


def _extract_body(soup: BeautifulSoup, title: str | None) -> str:
    containers = [node for node in soup.select(".post-content") if isinstance(node, Tag)]
    if not containers:
        article = soup.select_one("article")
        if isinstance(article, Tag):
            containers = [article]
    parts: list[str] = []
    seen: set[str] = set()
    for container in containers:
        fragment = BeautifulSoup(str(container), "html.parser")
        cleaned = fragment.find()
        if not isinstance(cleaned, Tag):
            continue
        for node in cleaned.find_all(_REMOVABLE_TAGS):
            node.decompose()
        for node in cleaned.find_all(_BODY_TAGS):
            if _should_skip_node(node):
                continue
            text = node.get_text(" ", strip=True)
            if not text:
                continue
            if title is not None and text == title:
                continue
            lowered = text.casefold()
            if any(snippet in lowered for snippet in _SKIP_TEXT_SNIPPETS):
                continue
            if text in seen:
                continue
            seen.add(text)
            parts.append(text)
    return "\n\n".join(parts).strip()


def _should_skip_node(node: Tag) -> bool:
    for ancestor in [node, *node.parents]:
        if not isinstance(ancestor, Tag):
            continue
        if _class_tokens(ancestor) & _SKIP_CLASS_TOKENS:
            return True
    return False


def _class_tokens(node: Tag) -> set[str]:
    tokens: set[str] = set()
    for class_name in node.get("class", []):
        value = str(class_name).strip().lower()
        if not value:
            continue
        tokens.add(value)
        tokens.update(part for part in value.replace("_", "-").split("-") if part)
    element_id = node.get("id")
    if isinstance(element_id, str):
        value = element_id.strip().lower()
        if value:
            tokens.add(value)
            tokens.update(part for part in value.replace("_", "-").split("-") if part)
    return tokens


def _article_metadata(soup: BeautifulSoup) -> dict[str, object]:
    for script in soup.select('script[type="application/ld+json"]'):
        if not isinstance(script, Tag):
            continue
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _json_ld_items(payload):
            if _is_news_article(item):
                return item
    return {}


def _json_ld_items(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        items = [payload]
        graph = payload.get("@graph")
        if isinstance(graph, list):
            items.extend(item for item in graph if isinstance(item, dict))
        return [item for item in items if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _is_news_article(item: dict[str, object]) -> bool:
    item_type = item.get("@type")
    if isinstance(item_type, str):
        return item_type in {"NewsArticle", "Article"}
    if isinstance(item_type, list):
        return any(isinstance(value, str) and value in {"NewsArticle", "Article"} for value in item_type)
    return False


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    node = soup.find("meta", attrs={attr: value})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None
