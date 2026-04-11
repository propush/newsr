from __future__ import annotations

from ...domain.articles import ArticleContent, SectionCandidate
from ..ninetofive.parsing import (
    NineToFiveSiteConfig,
    parse_site_article_html,
    parse_site_section_html,
)
from .urls import article_id_from_url, is_article_url, normalize_url

_SECTION_SELECTORS = (
    "main #posts .article__title-link",
    "main .river__posts .article__title-link",
    "main .article__title-link",
)
_REJECTED_TITLE_PREFIXES = (
    "9to5mac daily:",
    "happy hour:",
    "overtime:",
)
_REJECTED_TITLE_SNIPPETS = (
    "podcast",
    "buyers guide",
)
_SKIP_TEXT_SNIPPETS = (
    "check out 9to5mac on youtube",
    "ftc: we use income earning auto affiliate links.",
    "worth checking out on amazon",
    "you’re reading 9to5mac",
)
_SITE_CONFIG = NineToFiveSiteConfig(
    provider_id="9to5mac",
    section_selectors=_SECTION_SELECTORS,
    title_suffix=" - 9to5Mac",
    rejected_title_prefixes=_REJECTED_TITLE_PREFIXES,
    rejected_title_snippets=_REJECTED_TITLE_SNIPPETS,
    skip_text_snippets=_SKIP_TEXT_SNIPPETS,
    article_id_from_url=article_id_from_url,
    is_article_url=is_article_url,
    normalize_url=normalize_url,
)


def parse_section_html(html: str, category: str) -> list[SectionCandidate]:
    return parse_site_section_html(html, category, _SITE_CONFIG)


def parse_article_html(html: str, candidate: SectionCandidate) -> ArticleContent:
    return parse_site_article_html(html, candidate, _SITE_CONFIG)
