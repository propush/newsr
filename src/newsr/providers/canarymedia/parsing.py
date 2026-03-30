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
    "caption",
    "credit",
    "newsletter",
    "pagination",
    "promo",
    "related",
    "share",
    "sharing",
    "social",
    "sponsor",
    "sponsored",
    "subscribe",
}
_SKIP_TEXT_SNIPPETS = (
    "link copied to clipboard",
    "subscribe to canary media newsletters",
    "canary headlines plus top energy news",
)


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
                provider_id="canarymedia",
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
    return url


def _title_text(soup: BeautifulSoup) -> str | None:
    heading = soup.select_one("h1")
    if isinstance(heading, Tag):
        text = _normalize_whitespace(heading.get_text(" ", strip=True))
        if text:
            return text
    og_title = _meta_content(soup, "property", "og:title")
    if og_title:
        return _clean_title(og_title)
    return None


def _clean_title(value: str) -> str:
    cleaned = _normalize_whitespace(value)
    suffix = " | Canary Media"
    if cleaned.endswith(suffix):
        return cleaned[: -len(suffix)].rstrip()
    return cleaned


def _author_text(soup: BeautifulSoup) -> str | None:
    section = _article_section(soup)
    if section is not None:
        author_link = section.select_one('a[href*="/about/people/"]')
        if isinstance(author_link, Tag):
            cleaned = _clean_author(author_link.get_text(" ", strip=True))
            if cleaned:
                return cleaned
    return None


def _clean_author(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _normalize_whitespace(value)
    if cleaned.lower().startswith("by "):
        cleaned = cleaned[3:].strip()
    return cleaned or None


def _published_at(soup: BeautifulSoup) -> datetime | None:
    section = _article_section(soup)
    time_node = section.select_one("time[datetime]") if isinstance(section, Tag) else None
    if not isinstance(time_node, Tag):
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
    section = _article_section(soup)
    if section is None:
        return ""
    parts: list[str] = []
    seen: set[str] = set()
    for container in section.find_all(_is_prose_container):
        if not isinstance(container, Tag) or _should_skip_node(container):
            continue
        tagged_nodes = [node for node in container.find_all(_BODY_TAGS) if isinstance(node, Tag)]
        if tagged_nodes:
            for node in tagged_nodes:
                text = _body_text_from_node(node)
                if _should_skip_text(text, title) or text in seen:
                    continue
                seen.add(text)
                parts.append(text)
            continue
        text = _normalize_whitespace(container.get_text(" ", strip=True))
        if _should_skip_text(text, title) or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return "\n\n".join(parts).strip()


def _article_section(soup: BeautifulSoup) -> Tag | None:
    heading = soup.select_one("h1")
    if not isinstance(heading, Tag):
        return None
    return heading.find_parent("section")


def _body_text_from_node(node: Tag) -> str:
    return _normalize_whitespace(node.get_text(" ", strip=True))


def _should_skip_text(text: str, title: str | None) -> bool:
    if not text:
        return True
    lowered = text.casefold()
    if title is not None and text == title:
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


def _is_prose_container(tag: Tag) -> bool:
    return isinstance(tag, Tag) and "prose" in _class_tokens(tag)


def _class_tokens(node: Tag) -> set[str]:
    tokens: set[str] = set()
    for value in node.get("class", []):
        for token in re.split(r"[^a-z0-9]+", str(value).casefold()):
            if token:
                tokens.add(token)
    return tokens


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _meta_content(soup: BeautifulSoup, attr: str, name: str) -> str | None:
    node = soup.find("meta", attrs={attr: name})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None
