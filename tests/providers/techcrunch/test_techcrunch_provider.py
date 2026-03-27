from __future__ import annotations

from pathlib import Path

from newsr.domain import SectionCandidate
from newsr.providers.techcrunch import (
    BASE_TOPIC_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    TechCrunchProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)


def test_parse_section_html_extracts_unique_candidates_from_primary_query() -> None:
    html = Path("tests/fixtures/techcrunch_section.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "AI")

    assert [candidate.article_id for candidate in candidates] == [
        "2026/03/26/anthropic-wins-injunction-against-trump-administration-over-defense-department-saga",
        "2026/03/26/google-is-launching-search-live-globally",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/techcrunch_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="2026/03/26/google-is-launching-search-live-globally",
        provider_id="techcrunch",
        provider_article_id="2026/03/26/google-is-launching-search-live-globally",
        url="https://techcrunch.com/2026/03/26/google-is-launching-search-live-globally/",
        category="AI",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Google is launching Search Live globally"
    assert article.author == "Aisha Malik"
    assert article.published_at is not None
    assert "Google announced on Thursday" in article.body
    assert "Works on Android and iOS." in article.body
    assert "Get the best of TechCrunch" not in article.body
    assert "Topics" not in article.body


def test_discover_targets_returns_static_catalog() -> None:
    provider = TechCrunchProvider()

    default_targets = provider.default_targets()
    discovered_targets = provider.discover_targets()

    assert [target.target_key for target in discovered_targets] == [
        target.target_key for target in default_targets
    ]


def test_default_targets_mark_expected_core_targets_selected() -> None:
    targets = TechCrunchProvider().default_targets()

    assert [option.slug for option in BASE_TOPIC_OPTIONS] == [
        "latest",
        "startups",
        "venture",
        "ai",
        "security",
        "apps",
        "fintech",
        "enterprise",
        "climate",
        "robotics",
        "government-policy",
    ]
    assert {
        target.target_key for target in targets if target.selected
    } == DEFAULT_TARGET_SLUGS


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "https://www.techcrunch.com/2026/03/26/google-is-launching-search-live-globally?utm_source=rss"
    )

    assert url == "https://www.techcrunch.com/2026/03/26/google-is-launching-search-live-globally/"
    assert normalize_target_path("/category/security") == "/category/security/"
    assert is_article_url(url) is True
    assert is_article_url("https://techcrunch.com/tag/ai/") is False
    assert is_article_url("https://example.com/2026/03/26/google-is-launching-search-live-globally/") is False
    assert article_id_from_url(url) == "2026/03/26/google-is-launching-search-live-globally"
