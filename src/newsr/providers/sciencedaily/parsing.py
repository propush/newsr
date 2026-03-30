from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup, Tag

from ...domain.articles import ArticleContent, SectionCandidate
from .urls import article_id_from_url, is_article_url, normalize_url

_LISTING_SECTION_SELECTORS = (
    "#heroes",
    "#featured_blurbs",
    "#featured_shorts",
    "#summaries",
    "#headlines",
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for section in _listing_sections(soup):
        for link in section.select("a[href]"):
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
                    provider_id="sciencedaily",
                    provider_article_id=article_id,
                    url=article_url,
                    category=category,
                )
            )
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    title = _title_text(soup)
    author = _source_text(soup)
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


def _listing_sections(soup: BeautifulSoup) -> list[Tag]:
    sections: list[Tag] = []
    seen: set[int] = set()
    for selector in _LISTING_SECTION_SELECTORS:
        for node in soup.select(selector):
            if not isinstance(node, Tag):
                continue
            marker = id(node)
            if marker in seen:
                continue
            seen.add(marker)
            sections.append(node)
    if sections:
        return sections
    main = soup.select_one("main#main")
    if isinstance(main, Tag):
        return [main]
    return [soup]


def _article_url_from_link(link: Tag) -> str | None:
    href = str(link.get("href", "")).strip()
    if not href:
        return None
    url = normalize_url(href)
    if not is_article_url(url):
        return None
    return url


def _title_text(soup: BeautifulSoup) -> str | None:
    heading = soup.select_one("#headline")
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
    suffix = " -- ScienceDaily"
    if cleaned.endswith(suffix):
        return cleaned[: -len(suffix)].rstrip()
    return cleaned


def _source_text(soup: BeautifulSoup) -> str | None:
    node = soup.select_one("#source")
    if not isinstance(node, Tag):
        return None
    text = _normalize_whitespace(node.get_text(" ", strip=True))
    return text or None


def _published_at(soup: BeautifulSoup) -> datetime | None:
    node = soup.select_one("#date_posted")
    if not isinstance(node, Tag):
        return None
    raw = _normalize_whitespace(node.get_text(" ", strip=True))
    if not raw:
        return None
    return datetime.strptime(raw, "%B %d, %Y")


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
    story = soup.select_one("#story_text")
    if not isinstance(story, Tag):
        return ""
    parts: list[str] = []
    seen: set[str] = set()
    summary = _summary_text(soup)
    if summary:
        parts.append(summary)
        seen.add(summary)
    for node in [story.select_one("#first"), *story.select("#text p")]:
        if not isinstance(node, Tag):
            continue
        text = _normalize_whitespace(node.get_text(" ", strip=True))
        if not text or text == title or text in seen:
            continue
        parts.append(text)
        seen.add(text)
    return "\n\n".join(parts).strip()


def _summary_text(soup: BeautifulSoup) -> str | None:
    node = soup.select_one("#abstract")
    if not isinstance(node, Tag):
        return None
    text = _normalize_whitespace(node.get_text(" ", strip=True))
    return text or None


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _meta_content(soup: BeautifulSoup, attr: str, name: str) -> str | None:
    node = soup.find("meta", attrs={attr: name})
    if not isinstance(node, Tag):
        return None
    content = str(node.get("content", "")).strip()
    return content or None
