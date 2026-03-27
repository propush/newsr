from __future__ import annotations

from pathlib import Path

from newsr.domain import SectionCandidate
from newsr.providers.bbc import (
    BASE_CATEGORY_OPTIONS,
    BBCNewsProvider,
    DEFAULT_TARGET_SLUGS,
    is_article_url,
    merge_category_catalogs,
    parse_article_html,
    parse_category_catalog_html,
    parse_section_html,
)
from newsr.providers.bbc import CategoryOption


def test_parse_section_html_extracts_unique_candidates() -> None:
    html = Path("tests/fixtures/section.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "world")

    assert [candidate.article_id for candidate in candidates] == ["world-1", "world-2"]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="world-1",
        provider_id="bbc",
        provider_article_id="world-1",
        url="https://www.bbc.com/news/world-1",
        category="world",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Fixture headline"
    assert article.author == "Fixture Reporter"
    assert "First paragraph." in article.body


def test_parse_category_catalog_html_extracts_unique_categories() -> None:
    html = Path("tests/fixtures/categories.html").read_text(encoding="utf-8")

    categories = parse_category_catalog_html(html)

    assert [(category.slug, category.label) for category in categories] == [
        ("world", "World"),
        ("technology", "Technology"),
        ("entertainment_and_arts", "Entertainment & Arts"),
        ("science-environment", "Science Environment"),
    ]


def test_merge_category_catalogs_keeps_base_order_and_appends_discovered_extras() -> None:
    merged = merge_category_catalogs(
        [
            CategoryOption("world", "World"),
            CategoryOption("technology", "Technology"),
        ],
        [
            CategoryOption("technology", "Tech From BBC"),
            CategoryOption("us-canada", "US & Canada"),
            CategoryOption("uk", "UK"),
        ],
    )

    assert [(category.slug, category.label) for category in merged] == [
        ("world", "World"),
        ("technology", "Technology"),
        ("us-canada", "US & Canada"),
        ("uk", "UK"),
    ]


def test_discover_targets_merges_base_catalog_with_discovered_categories() -> None:
    html = Path("tests/fixtures/categories.html").read_text(encoding="utf-8")

    class StubProvider(BBCNewsProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    targets = StubProvider().discover_targets()
    slugs = [target.target_key for target in targets]

    assert slugs[: len(BASE_CATEGORY_OPTIONS)] == [category.slug for category in BASE_CATEGORY_OPTIONS]
    assert "world" in slugs
    assert "technology" in slugs
    assert "business" in slugs
    assert "health" in slugs
    assert "science-environment" in slugs


def test_base_category_catalog_contains_required_core_categories() -> None:
    slugs = {category.slug for category in BASE_CATEGORY_OPTIONS}

    assert {
        "world",
        "technology",
        "entertainment_and_arts",
        "business",
        "bbcindepth",
    }.issubset(slugs)


def test_default_targets_mark_expected_core_targets_selected() -> None:
    targets = BBCNewsProvider().default_targets()

    assert {
        target.target_key for target in targets if target.selected
    } == DEFAULT_TARGET_SLUGS


def test_is_article_url_rejects_section_and_live_pages() -> None:
    assert is_article_url("https://www.bbc.com/news/world-123") is True
    assert is_article_url("https://www.bbc.com/news/articles/cgr53z4dxpmo") is True
    assert is_article_url("https://www.bbc.com/news/world") is False
    assert is_article_url("https://www.bbc.com/news/live/cn047x0j52lt") is False
    assert is_article_url("https://www.bbc.com/news/topics/cx2pk70323et") is False
