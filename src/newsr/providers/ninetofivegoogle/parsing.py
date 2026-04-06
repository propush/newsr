from __future__ import annotations

import re
from datetime import datetime
from itertools import islice

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

_PRIMARY_SECTION_SELECTORS = (
    "main .article-list .article-item a",
    "main .post-list .post-item a",
    "main .article__title-link",
    "main .river__posts .article__title-link",
)
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
_REJECTED_TITLE_PREFIXES = (
    "9to5google daily:",
    "happy hour:",
    "overtime:",
)

_PODCAST_PATTERNS = (
    re.compile(r"^pixelated\s+\d+\s*:", re.IGNORECASE),
    re.compile(r"^the sideload\s+\d+\s*:", re.IGNORECASE),
)
_REJECTED_TITLE_SNIPPETS = (
    "buyers guide",
)
_SKIP_TEXT_SNIPPETS = (
    "check out 9to5google on youtube",
    "ftc: we use income earning auto affiliate links.",
    "worth checking out on amazon",
    "you're reading 9to5google",
    "you’re reading 9to5google",
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for link in _candidate_links(soup):
        article_url = _article_url_from_link(link)
        if article_url is None:
            continue
        article_id = article_id_from_url(article_url)
        if article_id in seen:
            continue
        seen.add(article_id)
        candidates.append(
            SectionCandidate(
                article_id=article_id,
                provider_id="ninetofivegoogle",
                provider_article_id=article_id,
                url=article_url,
                category=category,
            )
        )
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    title = _title_text(soup)
    author = _author_text(soup)
    published_at = _published_at(soup)
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


def _candidate_links(soup: BeautifulSoup) -> list[Tag]:
    seen_ids: set[int] = set()
    links: list[Tag] = []
    for selector in _PRIMARY_SECTION_SELECTORS:
        for link in soup.select(selector):
            if not isinstance(link, Tag):
                continue
            identity = id(link)
            if identity in seen_ids:
                continue
            seen_ids.add(identity)
            links.append(link)
    return links


def _article_url_from_link(link: Tag) -> str | None:
    if _should_skip_node(link):
        return None
    href = str(link.get("href", "")).strip()
    if not href:
        return None
    url = normalize_url(href)
    if not is_article_url(url):
        return None
    title = link.get_text(" ", strip=True)
    lowered = title.casefold()
    if any(lowered.startswith(prefix) for prefix in _REJECTED_TITLE_PREFIXES):
        return None
    if any(snippet in lowered for snippet in _REJECTED_TITLE_SNIPPETS):
        return None
    if any(pattern.match(title) for pattern in _PODCAST_PATTERNS):
        return None
    return url


def _title_text(soup: BeautifulSoup) -> str | None:
    heading = soup.select_one("#content h1.h1, #content h1")
    if isinstance(heading, Tag):
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    title = _meta_content(soup, "property", "og:title")
    if title:
        return _clean_title(title)
    return None


def _clean_title(value: str) -> str:
    cleaned = value.strip()
    suffix = " - 9to5Google"
    if cleaned.endswith(suffix):
        return cleaned[: -len(suffix)].rstrip()
    return cleaned


def _author_text(soup: BeautifulSoup) -> str | None:
    author = _meta_content(soup, "name", "author")
    if author:
        return author
    node = soup.select_one(
        "#content .post-meta .author__link a, "
        "#content .post-meta .author__link, "
        "#content .post-meta .author-name a, "
        "#content .post-meta .author-name"
    )
    if isinstance(node, Tag):
        text = node.get_text(" ", strip=True)
        if text:
            return text
    return None


def _published_at(soup: BeautifulSoup) -> datetime | None:
    published = _meta_content(soup, "property", "article:published_time")
    if not published:
        return None
    try:
        return datetime.fromisoformat(published.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _canonical_url(soup: BeautifulSoup) -> str | None:
    link = soup.find("link", rel="canonical")
    if isinstance(link, Tag):
        href = str(link.get("href", "")).strip()
        if href:
            return normalize_url(href)
    url = _meta_content(soup, "property", "og:url")
    if url:
        return normalize_url(url)
    return None


def _extract_body(soup: BeautifulSoup, title: str | None) -> str:
    container = _body_container(soup)
    if not isinstance(container, Tag):
        return ""
    cleaned = container
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
        if any(snippet in lowered for snippet in _SKIP_TEXT_SNIPPETS):
            continue
        if text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n\n".join(parts).strip()


def _body_container(soup: BeautifulSoup) -> Tag | None:
    for selector in (
        "#content .container.med.post-content",
        "#content .post-body",
    ):
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node
    return None


def _should_skip_node(node: Tag) -> bool:
    for ancestor in [node, *islice(node.parents, 100)]:
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
        tokens.update(part for part in value.replace("_", "-").split("-") if part)
    return tokens


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    node = soup.find("meta", attrs={attr: value})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None
