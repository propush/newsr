from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, is_research_hub_url, normalize_url

_BODY_TAGS = ("p", "h2", "h3", "h4", "li", "blockquote")
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
    "sup",
    "svg",
    "video",
}
_SKIP_CLASS_TOKENS = {
    "accordion",
    "ad",
    "aside",
    "caption",
    "credit",
    "endnotes",
    "footer",
    "modal",
    "newsletter",
    "promo",
    "pullquote",
    "related",
    "share",
    "sidebar",
    "social",
    "tooltip",
}
_REJECTED_CONTENT_TYPES = {
    "collection",
    "course",
    "dashboard",
    "from deloitte.com",
    "podcast",
    "summary",
    "video",
    "webcast",
}
_SKIP_TEXT_SNIPPETS = (
    "cover image by:",
    "deloitte insights and our research centers deliver proprietary research",
    "discover a world of insights with our video content",
    "download pdf",
    "for personalized content and settings",
    "learn about our services",
    "looking to stay on top of the latest news and trends",
    "to access the research report, visit",
    "your source for the issues and ideas that matter to your business today",
)
_MULTISPACE_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")


def parse_search_response(payload: str, category: str) -> list[SectionCandidate]:
    try:
        response = json.loads(payload)
    except json.JSONDecodeError:
        return []
    hits = response.get("hits", {}).get("hits", [])
    if not isinstance(hits, list):
        return []

    ranked: list[tuple[datetime | None, SectionCandidate]] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        source = hit.get("_source")
        if not isinstance(source, dict):
            continue
        candidate = _candidate_from_source(source, category)
        if candidate is None:
            continue
        ranked.append((_published_at_from_value(source.get("date-published")), candidate))

    ranked.sort(
        key=lambda item: item[0] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for _, candidate in ranked:
        if candidate.provider_article_id in seen:
            continue
        seen.add(candidate.provider_article_id)
        candidates.append(candidate)
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    metadata = _structured_article_metadata(soup)
    url = _canonical_url(soup, metadata) or candidate.url
    title = _title_text(soup, metadata) or candidate.provider_article_id
    author = _author_text(soup, metadata, url)
    published_at = _published_at(soup, metadata)
    if is_research_hub_url(url):
        body = _extract_research_hub_body(soup)
    else:
        body = _extract_article_body(soup)
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


def _candidate_from_source(source: dict[str, object], category: str) -> SectionCandidate | None:
    raw_url = source.get("url")
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None
    url = normalize_url(raw_url)
    page_type = _normalized_text(source.get("page-type"))
    content_type = _normalized_text(source.get("content-type"))
    if page_type == "insights-article":
        if content_type in _REJECTED_CONTENT_TYPES:
            return None
        if not is_article_url(url):
            return None
    elif page_type == "insights-research-hubs":
        if not is_research_hub_url(url):
            return None
    else:
        return None

    article_id = article_id_from_url(url)
    return SectionCandidate(
        article_id=article_id,
        provider_id="deloitteinsights",
        provider_article_id=article_id,
        url=url,
        category=category,
    )


def _title_text(soup: BeautifulSoup, metadata: dict[str, object]) -> str | None:
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


def _author_text(soup: BeautifulSoup, metadata: dict[str, object], url: str) -> str | None:
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
            return ", ".join(dict.fromkeys(names))
    if is_research_hub_url(url):
        return None
    names = [
        node.get_text(" ", strip=True)
        for node in soup.select(".cmp-di-profile-promo__name a")
        if isinstance(node, Tag) and node.get_text(" ", strip=True)
    ]
    if names:
        return ", ".join(dict.fromkeys(names))
    return _meta_content(soup, "name", "author")


def _published_at(soup: BeautifulSoup, metadata: dict[str, object]) -> datetime | None:
    published = metadata.get("datePublished")
    if isinstance(published, str):
        parsed = _published_at_from_value(published)
        if parsed is not None:
            return parsed
    return _published_at_from_value(_meta_content(soup, "property", "article:published_time"))


def _canonical_url(soup: BeautifulSoup, metadata: dict[str, object]) -> str | None:
    link = soup.find("link", rel="canonical")
    if isinstance(link, Tag):
        href = str(link.get("href", "")).strip()
        if href:
            return normalize_url(href)
    og_url = _meta_content(soup, "property", "og:url")
    if og_url:
        return normalize_url(og_url)
    url = metadata.get("url")
    if isinstance(url, str) and url.strip() and "/content/websites/" not in url:
        return normalize_url(url)
    return None


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
        graph = payload.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _extract_article_body(soup: BeautifulSoup) -> str:
    containers = soup.select(".bodyresponsivegridcontainer .cmp-di-text--line-height-large .cmp-text")
    if not containers:
        return ""
    parts: list[str] = []
    for container in containers:
        if not isinstance(container, Tag):
            continue
        fragment = BeautifulSoup(str(container), "html.parser")
        root = fragment.find()
        if not isinstance(root, Tag):
            continue
        for node in root.find_all(_REMOVABLE_TAGS):
            node.decompose()
        parts.extend(_iter_body_parts(root))
    return _clean_body_parts(parts)


def _extract_research_hub_body(soup: BeautifulSoup) -> str:
    parts: list[str] = []
    subtitle = soup.select_one(".cmp-subtitle__text")
    if isinstance(subtitle, Tag):
        text = subtitle.get_text(" ", strip=True)
        if text:
            parts.append(text)
    for node in soup.select(".cmp-di-text--medium__link-heading-social .cmp-text p"):
        if not isinstance(node, Tag):
            continue
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        parts.append(text)
    return _clean_body_parts(parts)


def _iter_body_parts(root: Tag) -> list[str]:
    parts: list[str] = []
    for node in root.find_all(_BODY_TAGS):
        if _should_skip_node(node):
            continue
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        parts.append(text)
    return parts


def _should_skip_node(node: Tag) -> bool:
    for ancestor in [node, *node.parents]:
        if not isinstance(ancestor, Tag):
            continue
        if ancestor.name in {"aside"}:
            return True
        if _class_tokens(ancestor) & _SKIP_CLASS_TOKENS:
            return True
    text = node.get_text(" ", strip=True).casefold()
    return any(snippet in text for snippet in _SKIP_TEXT_SNIPPETS)


def _clean_body_parts(parts: list[str]) -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = _MULTISPACE_RE.sub(" ", part).strip()
        normalized = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", normalized)
        if not normalized:
            continue
        lowered = normalized.casefold()
        if any(snippet in lowered for snippet in _SKIP_TEXT_SNIPPETS):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return "\n\n".join(cleaned).strip()


def _published_at_from_value(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        return None


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    node = soup.find("meta", attrs={attr: value})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None


def _normalized_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().casefold()


def _class_tokens(node: Tag) -> set[str]:
    tokens: set[str] = set()
    for value in node.get("class", []):
        text = str(value).strip().casefold()
        if text:
            tokens.add(text)
    return tokens
