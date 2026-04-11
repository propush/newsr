from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Pattern

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .published_time import parse_published_time

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
    "ad",
    "affiliate",
    "author",
    "bio",
    "comments",
    "comment",
    "disclaimer",
    "newsletter",
    "promo",
    "related",
    "share",
    "social",
    "subscribe",
    "visitor-promo",
    "youtube",
}
_BODY_CONTAINER_SELECTORS = (
    "#content .container.med.post-content",
    "#content .post-body",
)
_TITLE_SELECTOR = "#content h1.h1, #content h1"
_AUTHOR_SELECTOR = (
    "#content .post-meta .author__link a, "
    "#content .post-meta .author__link, "
    "#content .post-meta .author-name a, "
    "#content .post-meta .author-name"
)


@dataclass(frozen=True, slots=True)
class NineToFiveSiteConfig:
    provider_id: str
    section_selectors: tuple[str, ...]
    title_suffix: str
    rejected_title_prefixes: tuple[str, ...]
    rejected_title_snippets: tuple[str, ...]
    skip_text_snippets: tuple[str, ...]
    article_id_from_url: Callable[[str], str]
    is_article_url: Callable[[str], bool]
    normalize_url: Callable[[str], str]
    podcast_title_patterns: tuple[Pattern[str], ...] = ()


def parse_site_section_html(
    html: str,
    category: str,
    config: NineToFiveSiteConfig,
) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for link in _candidate_links(soup, config.section_selectors):
        article_url = _article_url_from_link(link, config)
        if article_url is None:
            continue
        article_id = config.article_id_from_url(article_url)
        if article_id in seen:
            continue
        seen.add(article_id)
        candidates.append(
            SectionCandidate(
                article_id=article_id,
                provider_id=config.provider_id,
                provider_article_id=article_id,
                url=article_url,
                category=category,
            )
        )
    return candidates


def parse_site_article_html(
    html: str,
    candidate: SectionCandidate,
    config: NineToFiveSiteConfig,
) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    title = _title_text(soup, config.title_suffix)
    return ArticleContent(
        article_id=candidate.article_id,
        provider_id=candidate.provider_id,
        provider_article_id=candidate.provider_article_id,
        url=_canonical_url(soup, config.normalize_url) or candidate.url,
        category=candidate.category,
        title=title or candidate.provider_article_id,
        author=_author_text(soup),
        published_at=_published_at(soup),
        body=_extract_body(soup, title, config.skip_text_snippets),
    )


def _candidate_links(soup: BeautifulSoup, selectors: tuple[str, ...]) -> list[Tag]:
    seen_ids: set[int] = set()
    links: list[Tag] = []
    for selector in selectors:
        for link in soup.select(selector):
            if not isinstance(link, Tag):
                continue
            identity = id(link)
            if identity in seen_ids:
                continue
            seen_ids.add(identity)
            links.append(link)
    return links


def _article_url_from_link(link: Tag, config: NineToFiveSiteConfig) -> str | None:
    if _should_skip_node(link):
        return None
    href = str(link.get("href", "")).strip()
    if not href:
        return None
    url = config.normalize_url(href)
    if not config.is_article_url(url):
        return None
    title = link.get_text(" ", strip=True)
    lowered = title.casefold()
    if any(lowered.startswith(prefix) for prefix in config.rejected_title_prefixes):
        return None
    if any(snippet in lowered for snippet in config.rejected_title_snippets):
        return None
    if any(pattern.match(title) for pattern in config.podcast_title_patterns):
        return None
    return url


def _title_text(soup: BeautifulSoup, title_suffix: str) -> str | None:
    heading = soup.select_one(_TITLE_SELECTOR)
    if isinstance(heading, Tag):
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    title = _meta_content(soup, "property", "og:title")
    if title:
        return _clean_title(title, title_suffix)
    return None


def _clean_title(value: str, title_suffix: str) -> str:
    cleaned = value.strip()
    if cleaned.endswith(title_suffix):
        return cleaned[: -len(title_suffix)].rstrip()
    return cleaned


def _author_text(soup: BeautifulSoup) -> str | None:
    author = _meta_content(soup, "name", "author")
    if author:
        return author
    node = soup.select_one(_AUTHOR_SELECTOR)
    if not isinstance(node, Tag):
        return None
    text = node.get_text(" ", strip=True)
    return text or None


def _published_at(soup: BeautifulSoup) -> datetime | None:
    return parse_published_time(_meta_content(soup, "property", "article:published_time"))


def _canonical_url(soup: BeautifulSoup, normalize_url: Callable[[str], str]) -> str | None:
    link = soup.find("link", rel="canonical")
    if isinstance(link, Tag):
        href = str(link.get("href", "")).strip()
        if href:
            return normalize_url(href)
    url = _meta_content(soup, "property", "og:url")
    if url:
        return normalize_url(url)
    return None


def _extract_body(
    soup: BeautifulSoup,
    title: str | None,
    skip_text_snippets: tuple[str, ...],
) -> str:
    container = _body_container(soup)
    if not isinstance(container, Tag):
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
        if not text:
            continue
        lowered = text.casefold()
        if title is not None and text == title:
            continue
        if any(snippet in lowered for snippet in skip_text_snippets):
            continue
        if text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n\n".join(parts).strip()


def _body_container(soup: BeautifulSoup) -> Tag | None:
    for selector in _BODY_CONTAINER_SELECTORS:
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node
    return None


def _should_skip_node(node: Tag) -> bool:
    for ancestor in [node, *node.parents]:
        if not isinstance(ancestor, Tag):
            continue
        if ancestor.name in _REMOVABLE_TAGS:
            return True
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
        tokens.update(part for part in re.split(r"[-_]", value) if part)
    return tokens


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    node = soup.find("meta", attrs={attr: value})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None
