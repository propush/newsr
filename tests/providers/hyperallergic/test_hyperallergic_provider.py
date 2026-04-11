from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.hyperallergic import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    HYPERALLERGIC_ROOT,
    HyperallergicProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/hyperallergic_listing_news.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "News")

    assert [candidate.article_id for candidate in candidates] == [
        "marica-vilcek-graceful-champion-of-immigrant-artists-dies-at-89",
        "uk-museums-hold-over-260-000-human-remains-report-finds",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/hyperallergic_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="times-person-of-the-year-swaps-construction-workers-for-tech-billionaires",
        provider_id="hyperallergic",
        provider_article_id="times-person-of-the-year-swaps-construction-workers-for-tech-billionaires",
        url="https://hyperallergic.com/times-person-of-the-year-swaps-construction-workers-for-tech-billionaires/",
        category="News",
    )

    article = parse_article_html(html, candidate)

    assert (
        article.url
        == "https://hyperallergic.com/times-person-of-the-year-swaps-construction-workers-for-tech-billionaires/"
    )
    assert article.title == "TIME’s “Person of the Year” Swaps Construction Workers for Tech Billionaires"
    assert article.author == "Rhea Nayyar"
    assert article.published_at is not None
    assert "TIME Magazine announced that its 2025 Person of the Year" in article.body
    assert "The tech oligarchs, decked out in sports jackets" in article.body
    assert "Subscribe to our newsletter" not in article.body
    assert "Get the best of Hyperallergic sent straight to your inbox." not in article.body


def test_default_targets_match_curated_hyperallergic_catalog() -> None:
    targets = HyperallergicProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "news",
        "reviews",
        "opinion",
        "film",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/tag/news/"},
        {"path": "/tag/reviews/"},
        {"path": "/tag/opinion/"},
        {"path": "/tag/film/"},
    ]
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/hyperallergic_listing_news.html").read_text(encoding="utf-8")

    class StubProvider(HyperallergicProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    target = ProviderTarget(
        provider_id="hyperallergic",
        target_key="news",
        target_kind="category",
        label="News",
        payload={"path": "/tag/news/"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=5)

    assert [(candidate.article_id, candidate.provider_article_id, candidate.category) for candidate in candidates] == [
        (
            "hyperallergic:marica-vilcek-graceful-champion-of-immigrant-artists-dies-at-89",
            "marica-vilcek-graceful-champion-of-immigrant-artists-dies-at-89",
            "News",
        ),
        (
            "hyperallergic:uk-museums-hold-over-260-000-human-remains-report-finds",
            "uk-museums-hold-over-260-000-human-remains-report-finds",
            "News",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/hyperallergic_article.html").read_text(encoding="utf-8")

    class StubProvider(HyperallergicProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="hyperallergic:times-person-of-the-year-swaps-construction-workers-for-tech-billionaires",
        provider_id="hyperallergic",
        provider_article_id="times-person-of-the-year-swaps-construction-workers-for-tech-billionaires",
        url="https://hyperallergic.com/times-person-of-the-year-swaps-construction-workers-for-tech-billionaires/",
        category="News",
    )

    article = StubProvider().fetch_article(candidate)

    assert (
        article.article_id
        == "hyperallergic:times-person-of-the-year-swaps-construction-workers-for-tech-billionaires"
    )
    assert article.provider_id == "hyperallergic"
    assert (
        article.provider_article_id
        == "times-person-of-the-year-swaps-construction-workers-for-tech-billionaires"
    )
    assert article.title == "TIME’s “Person of the Year” Swaps Construction Workers for Tech Billionaires"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://hyperallergic.com/times-person-of-the-year-swaps-construction-workers-for-tech-billionaires/?utm_source=test#top"
    )

    assert (
        url
        == "https://hyperallergic.com/times-person-of-the-year-swaps-construction-workers-for-tech-billionaires/"
    )
    assert normalize_target_path("tag/news") == "/tag/news/"
    assert is_article_url(url) is True
    assert is_article_url("https://hyperallergic.com/tag/news/") is False
    assert is_article_url("https://hyperallergic.com/author/rhea-nayyar/") is False
    assert is_article_url("https://hyperallergic.com/newsletters/") is False
    assert is_article_url("https://hyperallergic.com/about/") is False
    assert is_article_url("https://example.com/times-person-of-the-year/") is False
    assert (
        article_id_from_url(url)
        == "times-person-of-the-year-swaps-construction-workers-for-tech-billionaires"
    )


def test_registry_includes_hyperallergic_provider() -> None:
    registry = build_provider_registry()

    assert "hyperallergic" in registry
    assert registry["hyperallergic"].display_name == "Hyperallergic"
    assert HYPERALLERGIC_ROOT == "https://hyperallergic.com"
