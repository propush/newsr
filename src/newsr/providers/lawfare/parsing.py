from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

_BODY_TAGS = ("p", "h2", "h3", "h4", "li", "blockquote")
_REMOVABLE_TAGS = {
    "aside",
    "button",
    "figure",
    "footer",
    "form",
    "iframe",
    "img",
    "nav",
    "noscript",
    "picture",
    "script",
    "style",
    "svg",
}
_SKIP_CLASS_TOKENS = {
    "audio",
    "author",
    "authors",
    "bio",
    "caption",
    "contributor",
    "contributors",
    "credit",
    "footer",
    "hero",
    "newsletter",
    "podcast",
    "promo",
    "related",
    "share",
    "sharing",
    "social",
    "subscribe",
    "summary",
    "video",
    "webinar",
}
_SKIP_TEXT_SNIPPETS = (
    "back to top",
    "meet the authors",
    "more articles",
    "print this article",
    "read more",
    "share on",
    "subscribe to lawfare",
    "topics:",
)
_REJECTED_TITLE_PREFIXES = (
    "lawfare daily:",
    "lawfare live:",
    "no bull:",
    "rational security:",
)
_REJECTED_TITLE_SNIPPETS = (
    "podcast",
    "rapid response pod",
    "scaling laws",
    "video",
    "webinar",
)
_DATETIME_FORMATS = (
    "%A, %B %d, %Y, %I:%M %p",
    "%m/%d/%Y %I:%M:%S %p",
)
_MULTISPACE_RE = re.compile(r"\s+")
_STAR_BREAK_RE = re.compile(r"^(?:\*\s*){3,}$")


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main")
    if not isinstance(main, Tag):
        return []
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for link in main.select("a[href]"):
        if not isinstance(link, Tag):
            continue
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
                provider_id="lawfare",
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


def _article_url_from_link(link: Tag) -> str | None:
    if _should_skip_node(link):
        return None
    href = str(link.get("href", "")).strip()
    if not href:
        return None
    url = normalize_url(href)
    if not is_article_url(url):
        return None
    title = _normalize_whitespace(link.get_text(" ", strip=True))
    if _is_rejected_title(title):
        return None
    return url


def _title_text(soup: BeautifulSoup) -> str | None:
    heading = soup.select_one("h1.post-detail__title")
    if not isinstance(heading, Tag):
        heading = soup.select_one("h1")
    if isinstance(heading, Tag):
        text = _normalize_whitespace(heading.get_text(" ", strip=True))
        if text:
            return text
    title = _meta_content(soup, "property", "og:title")
    if title:
        return _clean_title(title)
    return None


def _clean_title(value: str) -> str:
    cleaned = _normalize_whitespace(value)
    suffix = " | Lawfare"
    if cleaned.endswith(suffix):
        return cleaned[: -len(suffix)].rstrip()
    return cleaned


def _author_text(soup: BeautifulSoup) -> str | None:
    names = [
        _normalize_whitespace(link.get_text(" ", strip=True))
        for link in soup.select(".post-detail__authors a[href]")
        if isinstance(link, Tag)
    ]
    names = [name for name in names if name]
    if names:
        return ", ".join(dict.fromkeys(names))
    author = _meta_content(soup, "name", "citation_author")
    return _normalize_whitespace(author) if author else None


def _published_at(soup: BeautifulSoup) -> datetime | None:
    date_node = soup.select_one(".post-detail__date")
    if isinstance(date_node, Tag):
        parsed = _parse_datetime(date_node.get_text(" ", strip=True))
        if parsed is not None:
            return parsed
    return _parse_datetime(_meta_content(soup, "name", "citation_date"))


def _parse_datetime(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    cleaned = _normalize_whitespace(raw)
    if not cleaned:
        return None
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
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
    container = soup.select_one(".post-detail__content")
    if not isinstance(container, Tag):
        return ""
    parts: list[str] = []
    seen: set[str] = set()
    for node in container.find_all(_BODY_TAGS):
        if not isinstance(node, Tag) or _should_skip_node(node):
            continue
        text = _normalize_whitespace(node.get_text(" ", strip=True))
        if _should_skip_text(text, title) or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n\n".join(parts).strip()


def _should_skip_text(text: str, title: str | None) -> bool:
    if not text:
        return True
    lowered = text.casefold()
    if title is not None and text == title:
        return True
    if _STAR_BREAK_RE.fullmatch(text):
        return True
    return any(snippet in lowered for snippet in _SKIP_TEXT_SNIPPETS)


def _should_skip_node(node: Tag) -> bool:
    for ancestor in [node, *node.parents]:
        if not isinstance(ancestor, Tag):
            continue
        if ancestor.name in _REMOVABLE_TAGS:
            return True
        if _class_tokens(ancestor) & _SKIP_CLASS_TOKENS:
            return True
    return False


def _is_rejected_title(title: str) -> bool:
    if not title:
        return True
    lowered = title.casefold()
    if lowered.startswith(_REJECTED_TITLE_PREFIXES):
        return True
    return any(snippet in lowered for snippet in _REJECTED_TITLE_SNIPPETS)


def _class_tokens(node: Tag) -> set[str]:
    tokens: set[str] = set()
    for value in node.get("class", []):
        for token in re.split(r"[^a-z0-9]+", str(value).casefold()):
            if token:
                tokens.add(token)
    return tokens


def _normalize_whitespace(value: str | None) -> str:
    if value is None:
        return ""
    return _MULTISPACE_RE.sub(" ", value).strip()


def _meta_content(soup: BeautifulSoup, attr: str, name: str) -> str | None:
    node = soup.find("meta", attrs={attr: name})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None
