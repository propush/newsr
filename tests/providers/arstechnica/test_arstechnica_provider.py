from __future__ import annotations

from pathlib import Path

from newsr.domain import SectionCandidate
from newsr.providers.arstechnica import (
    ARS_ROOT,
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    ArsTechnicaProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_from_article_cards() -> None:
    html = Path("tests/fixtures/arstechnica_section.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "Latest")

    assert [candidate.article_id for candidate in candidates] == [
        "gadgets/2026/03/first-ars-story",
        "security/2026/03/second-ars-story",
    ]


def test_parse_article_html_extracts_body_metadata_with_jsonld_fallback() -> None:
    html = Path("tests/fixtures/arstechnica_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="gadgets/2026/03/fixture-ars-story",
        provider_id="arstechnica",
        provider_article_id="gadgets/2026/03/fixture-ars-story",
        url="https://arstechnica.com/gadgets/2026/03/fixture-ars-story/",
        category="Gadgets",
    )

    article = parse_article_html(html, candidate)

    assert article.url == "https://arstechnica.com/gadgets/2026/03/fixture-ars-story/"
    assert article.title == "Fixture Ars Story"
    assert article.author == "Ashley Belanger"
    assert article.published_at is not None
    assert "Ars paragraph one explains the main development." in article.body
    assert "Why it matters" in article.body
    assert "First bullet point." in article.body
    assert "This caption should not appear." not in article.body
    assert "Share this story" not in article.body
    assert "Subscribe to the Ars newsletter" not in article.body


def test_discover_targets_returns_static_catalog() -> None:
    provider = ArsTechnicaProvider()

    default_targets = provider.default_targets()
    discovered_targets = provider.discover_targets()

    assert [target.target_key for target in discovered_targets] == [
        target.target_key for target in default_targets
    ]


def test_default_targets_mark_expected_core_targets_selected() -> None:
    targets = ArsTechnicaProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "latest",
        "gadgets",
        "science",
        "security",
        "tech-policy",
        "space",
        "ai",
    ]
    assert [target.target_kind for target in targets] == [
        "feed",
        "category",
        "category",
        "category",
        "category",
        "category",
        "category",
    ]
    assert targets[0].payload == {"path": "/"}
    assert targets[1].payload == {"path": "/gadgets/"}
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://www.arstechnica.com/gadgets/2026/03/fixture-ars-story/?utm_source=rss#comments"
    )

    assert url == "https://www.arstechnica.com/gadgets/2026/03/fixture-ars-story/"
    assert normalize_target_path("/gadgets") == "/gadgets/"
    assert is_article_url(url) is True
    assert is_article_url("https://arstechnica.com/gadgets/") is False
    assert is_article_url("https://arstechnica.com/author/example/") is False
    assert is_article_url("https://example.com/gadgets/2026/03/fixture-ars-story/") is False
    assert article_id_from_url(url) == "gadgets/2026/03/fixture-ars-story"


def test_registry_includes_arstechnica_provider() -> None:
    registry = build_provider_registry()

    assert "arstechnica" in registry
    assert registry["arstechnica"].display_name == "Ars Technica"
    assert ARS_ROOT == "https://arstechnica.com"
