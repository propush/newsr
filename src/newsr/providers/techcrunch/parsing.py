from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

_BODY_TAGS = ("p", "h2", "h3", "h4", "li", "blockquote")
_REMOVABLE_TAGS = {
    "aside",
    "figure",
    "form",
    "iframe",
    "img",
    "noscript",
    "script",
    "style",
    "svg",
}
_SKIP_CLASS_TOKENS = {
    "ad",
    "ads",
    "author",
    "bio",
    "newsletter",
    "promo",
    "related",
    "share",
    "social",
    "subscribe",
    "topics",
}
_SKIP_TEXT_SNIPPETS = (
    "get the best of techcrunch",
    "topics",
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for post in _primary_post_items(soup):
        article_url = _article_url_from_post(post)
        if article_url is None:
            continue
        article_id = article_id_from_url(article_url)
        if article_id in seen:
            continue
        seen.add(article_id)
        candidates.append(
            SectionCandidate(
                article_id=article_id,
                provider_id="techcrunch",
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


def _primary_post_items(soup: BeautifulSoup) -> list[Tag]:
    query = soup.select_one("main .wp-block-query .wp-block-post-template")
    if query is None:
        query = soup.select_one(".wp-block-query .wp-block-post-template")
    if query is None:
        return []
    return [
        post
        for post in query.find_all("li", class_="wp-block-post", recursive=False)
        if isinstance(post, Tag)
    ]


def _article_url_from_post(post: Tag) -> str | None:
    for link in post.select("a[href]"):
        href = str(link.get("href", "")).strip()
        if not href:
            continue
        url = normalize_url(href)
        if is_article_url(url):
            return url
    return None


def _title_text(soup: BeautifulSoup) -> str | None:
    title = _meta_content(soup, "property", "og:title")
    if title:
        return _clean_title(title)
    heading = soup.select_one("h1.article-hero__title, h1.wp-block-post-title, h1")
    if isinstance(heading, Tag):
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    return None


def _clean_title(value: str) -> str:
    cleaned = value.strip()
    suffix = " | TechCrunch"
    if cleaned.endswith(suffix):
        return cleaned[: -len(suffix)].rstrip()
    return cleaned


def _author_text(soup: BeautifulSoup) -> str | None:
    names: list[str] = []
    for node in soup.select(
        ".article-hero__authors .wp-block-tc23-author-card-name__link, "
        ".article-hero__authors .wp-block-tc23-author-card-name"
    ):
        if not isinstance(node, Tag):
            continue
        text = node.get_text(" ", strip=True)
        if text and text not in names:
            names.append(text)
    if names:
        return ", ".join(names)
    return _meta_content(soup, "name", "author")


def _published_at(soup: BeautifulSoup) -> datetime | None:
    published_raw = _meta_content(soup, "property", "article:published_time")
    if published_raw:
        return datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
    time_node = soup.select_one(".article-hero__authors time[datetime], time[datetime]")
    if not isinstance(time_node, Tag):
        return None
    raw = str(time_node.get("datetime", "")).strip()
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


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


def _body_container(soup: BeautifulSoup) -> Tag | None:
    for selector in (
        ".entry-content.wp-block-post-content",
        ".entry-content",
        ".wp-block-post-content",
    ):
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node
    return None


def _should_skip_node(node: Tag) -> bool:
    classes = _class_tokens(node)
    return bool(classes & _SKIP_CLASS_TOKENS)


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
