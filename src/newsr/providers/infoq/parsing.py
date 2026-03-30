from __future__ import annotations

import json
from datetime import datetime
from html import unescape

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

_ALLOWED_SECTION_PREFIXES = ("News about", "Articles about")
_BODY_TAGS = ("p", "h2", "h3", "h4", "li", "blockquote")
_REMOVABLE_TAGS = {
    "audio",
    "button",
    "figure",
    "form",
    "iframe",
    "img",
    "input",
    "noscript",
    "picture",
    "script",
    "source",
    "style",
    "svg",
}
_SKIP_CLASS_TOKENS = {
    "actions",
    "author",
    "bio",
    "newsletter",
    "rating",
    "related",
    "share",
    "sidebar",
    "social",
    "topics",
    "widget",
}
_SKIP_TEXT_SNIPPETS = (
    "about the author",
    "for full size image click here",
    "show less",
    "show more",
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for section in _article_bearing_sections(soup):
        for item in section.select("li[data-path]"):
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
                    provider_id="infoq",
                    provider_article_id=article_id,
                    url=article_url,
                    category=category,
                )
            )
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    metadata = _structured_article_metadata(soup)
    url = _canonical_url(soup, metadata) or candidate.url
    title = _title_text(soup, metadata) or candidate.provider_article_id
    author = _author_text(soup, metadata)
    published_at = _published_at(metadata)
    body = _extract_body(soup)
    return ArticleContent(
        article_id=candidate.article_id,
        provider_id=candidate.provider_id,
        provider_article_id=candidate.provider_article_id,
        url=url,
        category=candidate.category,
        title=title,
        author=author,
        published_at=published_at,
        body=body,
    )


def _article_bearing_sections(soup: BeautifulSoup) -> list[Tag]:
    sections: list[Tag] = []
    for container in soup.select("div.items"):
        heading = container.select_one("h2.heading__rss")
        if not isinstance(heading, Tag):
            continue
        heading_text = _normalized_text(heading.get_text(" ", strip=True))
        if not heading_text.startswith(_ALLOWED_SECTION_PREFIXES):
            continue
        content = container.select_one(".items__content")
        if isinstance(content, Tag):
            sections.append(content)
    return sections


def _article_url_from_item(item: Tag) -> str | None:
    raw_path = str(item.get("data-path", "")).strip()
    if not raw_path:
        title_link = item.select_one(".card__title a[href]")
        if not isinstance(title_link, Tag):
            return None
        raw_path = str(title_link.get("href", "")).strip()
    if not raw_path:
        return None
    url = normalize_url(raw_path)
    if not is_article_url(url):
        return None
    return url


def _structured_article_metadata(soup: BeautifulSoup) -> dict[str, object]:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not isinstance(script, Tag):
            continue
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _iter_jsonld_items(payload):
            item_type = item.get("@type")
            if isinstance(item_type, list):
                lowered = {str(value).casefold() for value in item_type}
            else:
                lowered = {str(item_type).casefold()}
            if {"article", "newsarticle"} & lowered:
                return item
    return {}


def _iter_jsonld_items(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _title_text(soup: BeautifulSoup, metadata: dict[str, object]) -> str | None:
    headline = metadata.get("headline")
    if isinstance(headline, str) and headline.strip():
        return unescape(headline.strip())
    heading = soup.select_one("article h1.heading, h1.heading, h1")
    if isinstance(heading, Tag):
        text = _normalized_text(heading.get_text(" ", strip=True))
        if text:
            return text
    return None


def _author_text(soup: BeautifulSoup, metadata: dict[str, object]) -> str | None:
    author = metadata.get("author")
    names: list[str] = []
    if isinstance(author, dict):
        name = author.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    elif isinstance(author, list):
        for item in author:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    if names:
        return ", ".join(dict.fromkeys(names))
    author_node = soup.select_one(".author")
    if isinstance(author_node, Tag):
        text = _normalized_text(author_node.get_text(" ", strip=True))
        text = text.removesuffix(" Show more Show less").strip()
        if text:
            return text
    return None


def _published_at(metadata: dict[str, object]) -> datetime | None:
    raw = metadata.get("datePublished")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return _parse_datetime(raw.strip())


def _canonical_url(soup: BeautifulSoup, metadata: dict[str, object]) -> str | None:
    link = soup.find("link", rel="canonical")
    if isinstance(link, Tag):
        href = str(link.get("href", "")).strip()
        if href:
            return normalize_url(href)
    main_entity = metadata.get("mainEntityOfPage")
    if isinstance(main_entity, dict):
        page_id = main_entity.get("@id")
        if isinstance(page_id, str) and page_id.strip():
            return normalize_url(page_id)
    return None


def _extract_body(soup: BeautifulSoup) -> str:
    container = soup.select_one(".article__data")
    if not isinstance(container, Tag):
        return ""
    fragment = BeautifulSoup(str(container), "html.parser")
    root = fragment.select_one(".article__data")
    if not isinstance(root, Tag):
        return ""
    for node in root.find_all(_REMOVABLE_TAGS):
        node.decompose()
    parts: list[str] = []
    seen: set[str] = set()
    for node in root.find_all(_BODY_TAGS):
        if _should_skip_node(node):
            continue
        text = _normalized_text(node.get_text(" ", strip=True))
        if not text or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n\n".join(parts).strip()


def _should_skip_node(node: Tag) -> bool:
    for ancestor in [node, *node.parents]:
        if not isinstance(ancestor, Tag):
            continue
        if ancestor.name in {"aside"}:
            return True
        if _class_tokens(ancestor) & _SKIP_CLASS_TOKENS:
            return True
    text = _normalized_text(node.get_text(" ", strip=True))
    if not text:
        return True
    lowered = text.casefold()
    if any(snippet in lowered for snippet in _SKIP_TEXT_SNIPPETS):
        return True
    if lowered.startswith("figure "):
        return True
    if lowered.startswith("source:"):
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
    return tokens


def _normalized_text(value: str) -> str:
    return " ".join(unescape(value).split())


def _parse_datetime(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
