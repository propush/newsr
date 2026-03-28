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
    "has-sponsor-banner",
    "post-card--is-sponsored",
    "sponsored",
}
_BODY_SKIP_CLASS_TOKENS = {
    "ad",
    "author",
    "byline",
    "form",
    "form-interruptor",
    "meta",
    "newsletter",
    "post-card",
    "post-card__wrapper",
    "post-social-share",
    "promo",
    "related",
    "recommended",
    "share",
    "sidebar",
    "social",
    "sponsored",
    "syndicated",
    "tags",
    "topics",
}
_SKIP_TEXT_SNIPPETS = (
    "from the medcity news network",
    "medcity news daily newsletter",
    "more from medcity news",
    "share a link to this article",
    "sign up and get the latest news in your inbox",
    "subscribe now",
    "we will never sell or share your information without your consent",
)
_REJECT_CARD_TEXT_SNIPPETS = (
    "[video]",
    "podcast",
    "presented by",
    "sponsored post",
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for wrapper in _archive_card_wrappers(soup):
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
                provider_id="medcitynews",
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


def _archive_card_wrappers(soup: BeautifulSoup) -> list[Tag]:
    container = soup.select_one(".archive__content")
    if not isinstance(container, Tag):
        return []
    wrappers = container.find_all("div", class_="post-card__wrapper", recursive=False)
    return [wrapper for wrapper in wrappers if isinstance(wrapper, Tag)]


def _article_url_from_wrapper(wrapper: Tag) -> str | None:
    if _should_skip_wrapper(wrapper):
        return None
    article = wrapper.find("article", class_="post-card")
    if not isinstance(article, Tag):
        return None
    data_url = str(article.get("data-url", "")).strip()
    if data_url:
        normalized = normalize_url(data_url)
        if is_article_url(normalized):
            return normalized
    for link in article.select("h2 a[href], h3 a[href], a[href]"):
        href = str(link.get("href", "")).strip()
        if not href:
            continue
        normalized = normalize_url(href)
        if is_article_url(normalized):
            return normalized
    return None


def _should_skip_wrapper(wrapper: Tag) -> bool:
    if _class_tokens(wrapper) & _WRAPPER_SKIP_CLASS_TOKENS:
        return True
    article = wrapper.find("article", class_="post-card")
    if isinstance(article, Tag) and _class_tokens(article) & _WRAPPER_SKIP_CLASS_TOKENS:
        return True
    text = wrapper.get_text(" ", strip=True).casefold()
    return any(snippet in text for snippet in _REJECT_CARD_TEXT_SNIPPETS)


def _title_text(soup: BeautifulSoup) -> str | None:
    title = _meta_content(soup, "property", "og:title")
    if title:
        return _clean_title(title)
    heading = soup.select_one(".post-single__title, h1")
    if isinstance(heading, Tag):
        text = heading.get_text(" ", strip=True)
        if text:
            return text
    return None


def _clean_title(value: str) -> str:
    cleaned = value.strip()
    suffix = " - MedCity News"
    if cleaned.endswith(suffix):
        return cleaned[: -len(suffix)].rstrip()
    return cleaned


def _author_text(soup: BeautifulSoup) -> str | None:
    meta_author = _meta_content(soup, "name", "author")
    if meta_author:
        return meta_author
    for selector in (
        ".post-single__byline-author a[href]",
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
        if not text:
            continue
        if title is not None and text == title:
            continue
        lowered = text.casefold()
        if any(snippet in lowered for snippet in _SKIP_TEXT_SNIPPETS):
            continue
        if lowered.startswith("photo:"):
            continue
        if text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n\n".join(parts).strip()


def _body_container(soup: BeautifulSoup) -> Tag | None:
    for selector in (".post-single__content", ".post-single__article .content"):
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node
    return None


def _should_skip_node(node: Tag) -> bool:
    for ancestor in [node, *node.parents]:
        if not isinstance(ancestor, Tag):
            continue
        if _class_tokens(ancestor) & _BODY_SKIP_CLASS_TOKENS:
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
