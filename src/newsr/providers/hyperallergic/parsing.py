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
_WRAPPER_SKIP_CLASS_TOKENS = {
    "sponsored",
}
_BODY_SKIP_CLASS_TOKENS = {
    "author",
    "byline",
    "caption",
    "comments",
    "footnotes",
    "newsletter",
    "promo",
    "related",
    "share",
    "signup",
    "social",
    "sponsor",
    "subscribe",
}
_SKIP_TEXT_SNIPPETS = (
    "subscribe to our newsletter",
    "get the best of hyperallergic sent straight to your inbox",
    "support hyperallergic",
)
_REJECT_CARD_TEXT_SNIPPETS = (
    "sponsored",
    "opportunities",
    "newsletter",
    "community announcements",
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for wrapper in _card_wrappers(soup):
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
                provider_id="hyperallergic",
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


def _card_wrappers(soup: BeautifulSoup) -> list[Tag]:
    feed = soup.select_one(".gh-feed")
    if isinstance(feed, Tag):
        return [node for node in feed.select("article.gh-card") if isinstance(node, Tag)]
    return [node for node in soup.select("article.gh-card") if isinstance(node, Tag)]


def _article_url_from_wrapper(wrapper: Tag) -> str | None:
    if _should_skip_wrapper(wrapper):
        return None
    link = wrapper.select_one("a.gh-card-link[href]")
    if not isinstance(link, Tag):
        return None
    href = str(link.get("href", "")).strip()
    if not href:
        return None
    normalized = normalize_url(href)
    if not is_article_url(normalized):
        return None
    return normalized


def _should_skip_wrapper(wrapper: Tag) -> bool:
    if _class_tokens(wrapper) & _WRAPPER_SKIP_CLASS_TOKENS:
        return True
    tag_label = wrapper.select_one(".gh-card-tag")
    if isinstance(tag_label, Tag):
        lowered_label = tag_label.get_text(" ", strip=True).casefold()
        if lowered_label in {"sponsored", "opportunities", "community"}:
            return True
    text = wrapper.get_text(" ", strip=True).casefold()
    return any(snippet in text for snippet in _REJECT_CARD_TEXT_SNIPPETS)


def _title_text(soup: BeautifulSoup) -> str | None:
    title = _meta_content(soup, "property", "og:title")
    if title:
        return title
    heading = soup.select_one(".gh-article-title, h1")
    if isinstance(heading, Tag):
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    return None


def _author_text(soup: BeautifulSoup) -> str | None:
    for selector in (
        ".gh-article-author-name a[href]",
        ".gh-article-author-name",
        'a[href*="/author/"]',
    ):
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return None


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
    if "T" in raw:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return datetime.fromisoformat(f"{raw}T00:00:00")


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
    container = soup.select_one(".gh-content")
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
        if _class_tokens(ancestor) & _BODY_SKIP_CLASS_TOKENS:
            return True
    return False


def _class_tokens(tag: Tag) -> set[str]:
    tokens: set[str] = set()
    classes = tag.get("class", [])
    if isinstance(classes, str):
        classes = classes.split()
    for value in classes:
        tokens.update(part.casefold() for part in str(value).split())
    return tokens


def _meta_content(soup: BeautifulSoup, attr_name: str, attr_value: str) -> str | None:
    node = soup.find("meta", attrs={attr_name: attr_value})
    if not isinstance(node, Tag):
        return None
    value = str(node.get("content", "")).strip()
    return value or None
