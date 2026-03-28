from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

_ALLOWED_CONTENT_TYPES = {"digital article"}
_BODY_CLASS_TOKENS = {
    "article-body",
    "body",
    "content",
    "main",
    "post-content",
    "story-body",
}
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
_BODY_TAGS = ("p", "h2", "h3", "h4", "li", "blockquote")
_SKIP_CLASS_TOKENS = {
    "ad",
    "ads",
    "caption",
    "credit",
    "footer",
    "hero",
    "newsletter",
    "promo",
    "pullquote",
    "related",
    "share",
    "sidebar",
    "social",
    "subscribe",
}
_SKIP_TEXT_SNIPPETS = (
    "buy copies",
    "download a pdf",
    "gift this article",
    "read more on",
    "save share",
    "share this article",
    "sign in subscribe",
)
_MULTISPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
_SPACE_AFTER_OPEN_QUOTE_RE = re.compile(r"([(\[{“‘])\s+")
_SPACE_BEFORE_CLOSE_QUOTE_RE = re.compile(r"\s+([)\]}”’])")


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for item in soup.select("stream-item[data-url]"):
        if not isinstance(item, Tag):
            continue
        article_url = _article_url_from_item(item)
        if article_url is None:
            continue
        article_id = article_id_from_url(article_url)
        if article_id in seen:
            continue
        seen.add(article_id)
        candidates.append(
            SectionCandidate(
                article_id=article_id,
                provider_id="hbr",
                provider_article_id=article_id,
                url=article_url,
                category=category,
            )
        )
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    next_article = _next_article_payload(soup)
    metadata = _structured_article_metadata(soup)
    title = _title_text(soup, next_article, metadata)
    author = _author_text(soup, next_article, metadata)
    published_at = _published_at(soup, next_article, metadata)
    url = _canonical_url(soup, next_article, metadata) or candidate.url
    body = _clean_body_text(
        _next_article_body(next_article)
        or _structured_article_body(metadata)
        or _extract_body_from_dom(soup, title)
    )
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


def _article_url_from_item(item: Tag) -> str | None:
    content_type = str(item.get("data-content-type", "")).strip().casefold()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        return None
    href = str(item.get("data-url", "")).strip()
    if not href:
        link = item.select_one('a[href^="/"][href]')
        if isinstance(link, Tag):
            href = str(link.get("href", "")).strip()
    if not href:
        return None
    url = normalize_url(href)
    if not is_article_url(url):
        return None
    return url


def _title_text(
    soup: BeautifulSoup, next_article: dict[str, object], metadata: dict[str, object]
) -> str | None:
    title = next_article.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    headline = metadata.get("headline")
    if isinstance(headline, str) and headline.strip():
        return headline.strip()
    og_title = _meta_content(soup, "property", "og:title")
    if og_title:
        return og_title
    heading = soup.select_one("h1")
    if isinstance(heading, Tag):
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    return None


def _author_text(
    soup: BeautifulSoup, next_article: dict[str, object], metadata: dict[str, object]
) -> str | None:
    authors = next_article.get("authors")
    if isinstance(authors, list):
        names = [
            name.strip()
            for author in authors
            if isinstance(author, dict)
            for name in [author.get("name")]
            if isinstance(name, str) and name.strip()
        ]
        if names:
            return ", ".join(names)
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
    meta_author = _meta_content(soup, "name", "author")
    if meta_author:
        return meta_author
    return None


def _published_at(
    soup: BeautifulSoup, next_article: dict[str, object], metadata: dict[str, object]
) -> datetime | None:
    published = next_article.get("published")
    if isinstance(published, str) and published.strip():
        return _published_at_from_value(published)
    published = metadata.get("datePublished")
    if isinstance(published, str) and published.strip():
        return _published_at_from_value(published)
    published = _meta_content(soup, "property", "article:published_time")
    return _published_at_from_value(published)


def _published_at_from_value(value: str | None) -> datetime | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))


def _canonical_url(
    soup: BeautifulSoup, next_article: dict[str, object], metadata: dict[str, object]
) -> str | None:
    link = soup.find("link", rel="canonical")
    if isinstance(link, Tag):
        href = str(link.get("href", "")).strip()
        if href:
            return normalize_url(href)
    url = metadata.get("url")
    if isinstance(url, str) and url.strip():
        return normalize_url(url)
    return None


def _next_article_payload(soup: BeautifulSoup) -> dict[str, object]:
    script = soup.find("script", attrs={"id": "__NEXT_DATA__", "type": "application/json"})
    if not isinstance(script, Tag):
        return {}
    raw = script.string or script.get_text()
    if not raw or not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    props = payload.get("props")
    if not isinstance(props, dict):
        return {}
    page_props = props.get("pageProps")
    if not isinstance(page_props, dict):
        return {}
    article = page_props.get("article")
    if not isinstance(article, dict):
        return {}
    return article


def _next_article_body(next_article: dict[str, object]) -> str | None:
    body = next_article.get("articleBody")
    if isinstance(body, str) and body.strip():
        return body
    content = next_article.get("content")
    if isinstance(content, str) and content.strip():
        fragment = BeautifulSoup(content, "html.parser")
        return fragment.get_text("\n\n", strip=True) or None
    return None


def _extract_body_from_dom(soup: BeautifulSoup, title: str | None) -> str:
    containers = [
        node
        for node in soup.select("main article, article, [itemprop='articleBody']")
        if isinstance(node, Tag)
    ]
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
            if _should_skip_body_node(node):
                continue
            text = _clean_body_text(node.get_text(" ", strip=True))
            if not text:
                continue
            if title is not None and text == title:
                continue
            if text in seen:
                continue
            seen.add(text)
            parts.append(text)
    return "\n\n".join(parts).strip()


def _should_skip_body_node(node: Tag) -> bool:
    for ancestor in [node, *node.parents]:
        if not isinstance(ancestor, Tag):
            continue
        if _class_tokens(ancestor) & _SKIP_CLASS_TOKENS:
            return True
    text = node.get_text(" ", strip=True).casefold()
    return any(snippet in text for snippet in _SKIP_TEXT_SNIPPETS)


def _clean_body_text(value: str | None) -> str:
    if value is None:
        return ""
    cleaned = unescape(value).replace("\xa0", " ").strip()
    cleaned = _MULTISPACE_RE.sub(" ", cleaned)
    cleaned = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned)
    cleaned = _SPACE_AFTER_OPEN_QUOTE_RE.sub(r"\1", cleaned)
    cleaned = _SPACE_BEFORE_CLOSE_QUOTE_RE.sub(r"\1", cleaned)
    return cleaned.strip()


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


def _structured_article_metadata(soup: BeautifulSoup) -> dict[str, object]:
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
            if _is_article(item):
                return item
    return {}


def _structured_article_body(metadata: dict[str, object]) -> str | None:
    body = metadata.get("articleBody")
    if isinstance(body, str) and body.strip():
        return body
    return None


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


def _is_article(item: dict[str, object]) -> bool:
    item_type = item.get("@type")
    if isinstance(item_type, str):
        return item_type in {"Article", "NewsArticle"}
    if isinstance(item_type, list):
        return any(isinstance(value, str) and value in {"Article", "NewsArticle"} for value in item_type)
    return False


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    node = soup.find("meta", attrs={attr: value})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None
