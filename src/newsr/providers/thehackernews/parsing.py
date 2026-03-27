from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, NavigableString, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

_BODY_CONTAINER_SELECTORS = (
    ".articlebody",
    ".article-body",
    ".blog-posts",
    ".entry-content",
    ".post-body",
    "article",
    "main",
)
_BODY_METADATA_SELECTORS = (
    "h1",
    "time",
    ".author",
    ".author-box",
    ".byline",
    ".post-author",
    ".entry-meta",
    ".post-meta",
    ".article-meta",
    ".post-header",
)
_BLOCK_TAGS = {
    "article",
    "aside",
    "blockquote",
    "div",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "main",
    "ol",
    "p",
    "pre",
    "section",
    "ul",
}
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
    "style",
    "svg",
    "video",
}
_SKIP_CONTAINER_TOKENS = {
    "author",
    "banner",
    "comment",
    "footer",
    "header",
    "newsletter",
    "promo",
    "related",
    "share",
    "sidebar",
    "social",
    "sponsored",
    "subscribe",
    "widget",
}
_SKIP_TEXT_SNIPPETS = (
    "get latest news in your inbox",
    "follow us on",
    "free ebook",
    "register for this webinar",
    "click here to register",
    "sponsored",
)
_NON_ALNUM_PATTERN = re.compile(r"[\W_]+")
_SITE_AUTHOR_PLACEHOLDER = "The Hacker News"


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    scope = soup.find("main") or soup
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for link in scope.select("a[href]"):
        href = str(link.get("href", "")).strip()
        if not href:
            continue
        url = normalize_url(href)
        if not is_article_url(url):
            continue
        article_id = article_id_from_url(url)
        if article_id in seen:
            continue
        seen.add(article_id)
        candidates.append(
            SectionCandidate(
                article_id=article_id,
                provider_id="thehackernews",
                provider_article_id=article_id,
                url=url,
                category=category,
            )
        )
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    title = _first_text(soup, ["h1", 'meta[property="og:title"]', "title"])
    author = _author_text(soup)
    published_at = _published_at(soup)
    body = _extract_body(soup, title)
    return ArticleContent(
        article_id=candidate.article_id,
        provider_id=candidate.provider_id,
        provider_article_id=candidate.provider_article_id,
        url=candidate.url,
        category=candidate.category,
        title=title or candidate.provider_article_id,
        author=author,
        published_at=published_at,
        body=body,
    )


def _extract_body(soup: BeautifulSoup, title: str | None) -> str:
    container = _prepare_body_container(_find_body_container(soup))
    lines: list[str] = []
    fragments: list[str] = []

    def flush() -> None:
        text = _normalize_whitespace(" ".join(fragments))
        fragments.clear()
        if not text:
            return
        if title is not None and _comparable_text(text) == _comparable_text(title):
            return
        lowered = text.lower()
        if any(snippet in lowered for snippet in _SKIP_TEXT_SNIPPETS):
            return
        if lines and _comparable_text(lines[-1]) == _comparable_text(text):
            return
        lines.append(text)

    def walk(node: Tag | NavigableString) -> None:
        if isinstance(node, NavigableString):
            text = _normalize_whitespace(str(node))
            if text:
                fragments.append(text)
            return
        if node.name in _REMOVABLE_TAGS or _should_skip_node(node):
            flush()
            return
        if node.name == "br":
            flush()
            return
        is_block = node.name in _BLOCK_TAGS
        if is_block:
            flush()
        for child in node.children:
            if isinstance(child, (NavigableString, Tag)):
                walk(child)
        if is_block:
            flush()

    walk(container)
    flush()
    return "\n\n".join(lines).strip()


def _find_body_container(soup: BeautifulSoup) -> Tag:
    for selector in _BODY_CONTAINER_SELECTORS:
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node
    return soup


def _prepare_body_container(container: Tag) -> Tag:
    fragment = BeautifulSoup(str(container), "html.parser")
    cleaned = fragment.find()
    if not isinstance(cleaned, Tag):
        return fragment
    for selector in _BODY_METADATA_SELECTORS:
        for node in cleaned.select(selector):
            node.decompose()
    return cleaned


def _should_skip_node(node: Tag) -> bool:
    for ancestor in [node, *node.parents]:
        if not isinstance(ancestor, Tag):
            continue
        tokens = _tag_tokens(ancestor)
        if tokens & _SKIP_CONTAINER_TOKENS:
            return True
    return False


def _tag_tokens(node: Tag) -> set[str]:
    tokens: set[str] = set()
    class_names = node.get("class")
    if isinstance(class_names, list):
        for value in class_names:
            tokens.update(_split_tokens(value))
    element_id = node.get("id")
    if isinstance(element_id, str):
        tokens.update(_split_tokens(element_id))
    return tokens


def _split_tokens(value: str) -> set[str]:
    normalized = value.replace("_", "-").lower()
    parts = {part for part in normalized.split("-") if part}
    if normalized:
        parts.add(normalized)
    return parts


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _comparable_text(value: str) -> str:
    return _NON_ALNUM_PATTERN.sub("", value).casefold()


def _author_text(soup: BeautifulSoup) -> str | None:
    meta_author = _meta_content(soup, "name", "author")
    if meta_author:
        return _clean_author_text(meta_author)
    author_link = soup.select_one('a[rel="author"], [itemprop="author"]')
    if isinstance(author_link, Tag):
        text = author_link.get_text(" ", strip=True)
        if text:
            return _clean_author_text(text)
    byline = soup.select_one(".author, .byline, .post-author")
    if isinstance(byline, Tag):
        text = byline.get_text(" ", strip=True)
        if text:
            return _clean_author_text(text.removeprefix("by ").strip())
    return None


def _clean_author_text(value: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if _comparable_text(cleaned) == _comparable_text(_SITE_AUTHOR_PLACEHOLDER):
        return None
    return cleaned


def _published_at(soup: BeautifulSoup) -> datetime | None:
    raw = _meta_content(soup, "property", "article:published_time")
    if not raw:
        time_node = soup.select_one("time[datetime]")
        if isinstance(time_node, Tag):
            raw = str(time_node.get("datetime", "")).strip() or None
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    node = soup.find("meta", attrs={attr: value})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if not isinstance(node, Tag):
            continue
        if node.name == "meta":
            content = str(node.get("content", "")).strip()
            if content:
                return content
            continue
        text = node.get_text(" ", strip=True)
        if text:
            return text
    return None
