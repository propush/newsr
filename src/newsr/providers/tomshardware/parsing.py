from __future__ import annotations

import json
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

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
    "svg",
}
_SKIP_CLASS_TOKENS = {
    "caption",
    "comments",
    "credit",
    "hawkbroadband",
    "newsletter",
    "promo",
    "related",
    "share",
    "sharing",
    "sidebar",
    "social",
    "sponsored",
}
_SKIP_TEXT_SNIPPETS = (
    "article continues below",
    "go deeper with th premium",
    "here's how it works",
    "join the conversation",
    "share this article",
    "stay on the cutting edge: get the tom's hardware newsletter",
    "when you purchase through links on our site, we may earn an affiliate commission",
    "you may like",
)
_VALID_RESULT_TYPES = {
    "search-result-news",
    "search-result-review",
}
_INVALID_RESULT_TYPES = {
    "search-result-best-pick",
    "search-result-deals",
    "search-result-gallery",
}


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for wrapper in soup.select(".listingResult"):
        if not isinstance(wrapper, Tag):
            continue
        article_url = _article_url_from_wrapper(wrapper)
        if article_url is None:
            continue
        article_id = article_id_from_url(article_url)
        if article_id in seen:
            continue
        seen.add(article_id)
        candidates.append(
            SectionCandidate(
                article_id=article_id,
                provider_id="tomshardware",
                provider_article_id=article_id,
                url=article_url,
                category=category,
            )
        )
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    metadata = _structured_article_metadata(soup)
    title = _title_text(soup) or metadata.get("title")
    author = _author_text(soup) or metadata.get("author")
    published_at = _published_at(soup) or _published_at_from_value(metadata.get("published_at"))
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


def _article_url_from_wrapper(wrapper: Tag) -> str | None:
    article = wrapper.select_one("article.search-result")
    if not isinstance(article, Tag):
        return None
    classes = set(article.get("class", []))
    if classes & _INVALID_RESULT_TYPES:
        return None
    if not classes & _VALID_RESULT_TYPES:
        return None
    if "sponsored-post" in wrapper.get_text(" ", strip=True).casefold():
        return None
    link = wrapper.select_one("a.article-link[href]")
    if not isinstance(link, Tag):
        return None
    href = str(link.get("href", "")).strip()
    if not href:
        return None
    normalized = normalize_url(href)
    if not is_article_url(normalized):
        return None
    return normalized


def _title_text(soup: BeautifulSoup) -> str | None:
    og_title = _meta_content(soup, "property", "og:title")
    if og_title:
        return _clean_title(og_title)
    heading = soup.select_one("h1")
    if isinstance(heading, Tag):
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    return None


def _clean_title(value: str) -> str:
    cleaned = value.strip()
    suffix = " | Tom's Hardware"
    if cleaned.endswith(suffix):
        return cleaned[: -len(suffix)].rstrip()
    return cleaned


def _author_text(soup: BeautifulSoup) -> str | None:
    for selector in (
        '[rel="author"]',
        ".byline .by-author",
        ".byline a[href]",
        ".author-name",
    ):
        node = soup.select_one(selector)
        if not isinstance(node, Tag):
            continue
        text = node.get_text(" ", strip=True)
        cleaned = _clean_author(text)
        if cleaned:
            return cleaned
    return None


def _clean_author(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned.lower().startswith("by "):
        cleaned = cleaned[3:].strip()
    if cleaned.lower().startswith("by "):
        cleaned = cleaned[3:].strip()
    return cleaned or None


def _published_at(soup: BeautifulSoup) -> datetime | None:
    raw = _meta_content(soup, "property", "article:published_time")
    if raw:
        return _published_at_from_value(raw)
    time_node = soup.select_one("time[datetime]")
    if not isinstance(time_node, Tag):
        return None
    raw = str(time_node.get("datetime", "")).strip()
    return _published_at_from_value(raw)


def _published_at_from_value(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
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
    container = _body_container(soup)
    if container is None:
        return ""
    fragment = BeautifulSoup(str(container), "html.parser")
    cleaned = fragment.find()
    if not isinstance(cleaned, Tag):
        return ""
    for node in cleaned.find_all(_REMOVABLE_TAGS):
        node.decompose()
    parts: list[str] = []
    seen: set[str] = set()
    for node in cleaned.find_all(_BODY_TAGS):
        if _should_skip_node(node):
            continue
        text = node.get_text(" ", strip=True)
        if not text or (title is not None and text == title):
            continue
        lowered = text.casefold()
        if any(snippet in lowered for snippet in _SKIP_TEXT_SNIPPETS):
            continue
        if text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n\n".join(parts).strip()


def _body_container(soup: BeautifulSoup) -> Tag | None:
    for selector in (
        "#article-body",
        ".text-copy.bodyCopy",
        ".bodyCopy",
        "article",
    ):
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node
    return None


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


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    node = soup.find("meta", attrs={attr: value})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None


def _structured_article_metadata(soup: BeautifulSoup) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not isinstance(script, Tag):
            continue
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _json_items(payload):
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type")
            if item_type not in {"NewsArticle", "Review", "Article"}:
                continue
            headline = item.get("headline")
            if isinstance(headline, str) and headline.strip():
                metadata["title"] = headline.strip()
            author = item.get("author")
            if isinstance(author, dict):
                name = author.get("name")
                if isinstance(name, str) and name.strip():
                    metadata["author"] = name.strip()
            published = item.get("datePublished")
            if isinstance(published, str) and published.strip():
                metadata["published_at"] = published.strip()
            if metadata:
                return metadata
    return metadata


def _json_items(payload: object) -> list[object]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
        return list(payload["@graph"])
    return [payload]
