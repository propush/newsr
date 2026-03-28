from __future__ import annotations

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
    "ad",
    "ads",
    "author",
    "bio",
    "byline",
    "caption",
    "credit",
    "footer",
    "hero",
    "image",
    "newsletter",
    "promo",
    "related",
    "share",
    "social",
    "sponsor",
    "sponsored",
    "subscribe",
    "trendline",
}
_SKIP_TEXT_SNIPPETS = (
    "explore the trendline",
    "get the free newsletter",
    "read more:",
    "share this article",
    "sign up for the free newsletter",
    "subscribe to marketing dive",
)
_REJECT_CARD_TEXT_SNIPPETS = (
    "[video]",
    "explore the trendline",
    "sponsored by",
    "trendline",
    "webinar",
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for scope in _candidate_scopes(soup):
        article_url = _article_url_from_scope(scope)
        if article_url is None:
            continue
        article_id = article_id_from_url(article_url)
        if article_id in seen:
            continue
        seen.add(article_id)
        candidates.append(
            SectionCandidate(
                article_id=article_id,
                provider_id="marketingdive",
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


def _candidate_scopes(soup: BeautifulSoup) -> list[Tag]:
    selectors = (
        "main article",
        "article",
        "main li",
        ".feed__item",
        ".topic-feed__item",
    )
    scopes: list[Tag] = []
    seen: set[int] = set()
    for selector in selectors:
        for node in soup.select(selector):
            if not isinstance(node, Tag):
                continue
            marker = id(node)
            if marker in seen:
                continue
            seen.add(marker)
            scopes.append(node)
    if scopes:
        return scopes
    main = soup.select_one("main")
    if isinstance(main, Tag):
        return [main]
    return [soup]


def _article_url_from_scope(scope: Tag) -> str | None:
    if _should_skip_scope(scope):
        return None
    for selector in ("h1 a[href]", "h2 a[href]", "h3 a[href]", "h4 a[href]", "a[href]"):
        for link in scope.select(selector):
            href = str(link.get("href", "")).strip()
            if not href:
                continue
            url = normalize_url(href)
            if is_article_url(url):
                return url
    return None


def _should_skip_scope(scope: Tag) -> bool:
    lowered = scope.get_text(" ", strip=True).casefold()
    if any(snippet in lowered for snippet in _REJECT_CARD_TEXT_SNIPPETS):
        return True
    return bool(_class_tokens(scope) & _SKIP_CLASS_TOKENS)


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
    suffix = " | Marketing Dive"
    if cleaned.endswith(suffix):
        return cleaned[: -len(suffix)].rstrip()
    return cleaned


def _author_text(soup: BeautifulSoup) -> str | None:
    meta_author = _meta_content(soup, "name", "author")
    if meta_author:
        return _clean_author(meta_author)
    for selector in (
        '[rel="author"]',
        '[itemprop="author"] [itemprop="name"]',
        '[itemprop="author"] a[href]',
        ".byline a[href]",
        ".byline .author",
        ".byline .author-name",
        ".author-name",
        ".author",
    ):
        for node in soup.select(selector):
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
    return cleaned or None


def _published_at(soup: BeautifulSoup) -> datetime | None:
    published_raw = _meta_content(soup, "property", "article:published_time")
    if published_raw:
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
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
        '[itemprop="articleBody"]',
        ".article-body",
        ".article-content",
        ".entry-content",
        "main article",
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
