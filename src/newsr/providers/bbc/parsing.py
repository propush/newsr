from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup

from ...domain.articles import ArticleContent, SectionCandidate
from .categories import CategoryOption
from .urls import article_id_from_url, category_slug_from_url, is_article_url, label_from_slug, normalize_url


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    candidates: list[SectionCandidate] = []
    for link in soup.select("a[href]"):
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
                provider_id="bbc",
                provider_article_id=article_id,
                url=url,
                category=category,
            )
        )
    return candidates


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    soup = BeautifulSoup(html, "html.parser")
    title = _first_text(soup, ["h1", 'meta[property="og:title"]'])
    author = _meta_content(soup, "name", "byl")
    published_raw = _meta_content(soup, "property", "article:published_time")
    published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00")) if published_raw else None
    body = _extract_body(soup)
    return ArticleContent(
        article_id=candidate.article_id,
        provider_id=candidate.provider_id,
        provider_article_id=candidate.provider_article_id,
        url=candidate.url,
        category=candidate.category,
        title=title or candidate.article_id,
        author=author,
        published_at=published_at,
        body=body,
    )


def parse_category_catalog_html(html: str) -> list[CategoryOption]:
    soup = BeautifulSoup(html, "html.parser")
    categories_by_slug: dict[str, CategoryOption] = {}
    for link in soup.select("a[href]"):
        href = str(link.get("href", "")).strip()
        slug = category_slug_from_url(normalize_url(href))
        if slug is None or slug in categories_by_slug:
            continue
        label = _normalize_label(link.get_text(" ", strip=True)) or label_from_slug(slug)
        categories_by_slug[slug] = CategoryOption(slug=slug, label=label)
    return list(categories_by_slug.values())


def _extract_body(soup: BeautifulSoup) -> str:
    article = soup.find("article") or soup.find("main") or soup
    paragraphs = [node.get_text(" ", strip=True) for node in article.select("p")]
    text = "\n\n".join(part for part in paragraphs if part)
    return text.strip()


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    node = soup.find("meta", attrs={attr: value})
    if node is None:
        return None
    content = str(node.get("content", "")).strip()
    return content or None


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node is None:
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


def _normalize_label(value: str) -> str | None:
    parts = value.split()
    if not parts:
        return None
    return " ".join(parts)
