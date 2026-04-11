from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.canarymedia import (
    BASE_TARGET_OPTIONS,
    CANARYMEDIA_ROOT,
    DEFAULT_TARGET_SLUGS,
    CanaryMediaProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/canarymedia_listing_grid_edge.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "Grid Edge")

    assert [candidate.article_id for candidate in candidates] == [
        "articles/utilities/as-californians-electrify-tech-prevent-grid-overload",
        "articles/grid-edge/winter-storm-fern-grid-renewables-gas",
        "articles/transportation/plug-more-evs-into-grid-report",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/canarymedia_article_grid_storage_goal.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="articles/energy-storage/grid-storage-industry-crushes-2025-goal",
        provider_id="canarymedia",
        provider_article_id="articles/energy-storage/grid-storage-industry-crushes-2025-goal",
        url="https://www.canarymedia.com/articles/energy-storage/grid-storage-industry-crushes-2025-goal",
        category="Energy Storage",
    )

    article = parse_article_html(html, candidate)

    assert (
        article.url
        == "https://www.canarymedia.com/articles/energy-storage/grid-storage-industry-crushes-2025-goal"
    )
    assert article.title == "The grid storage industry set a wild goal for 2025 - and then crushed it"
    assert article.author == "Julian Spector"
    assert article.published_at is not None
    assert "In 2017, U.S. grid storage developers promised they could deliver 35 gigawatts by 2025." in article.body
    assert "Storage has become the dominant form of new power addition, Kathpal said." in article.body
    assert "Developers built projects faster than early forecasts expected." in article.body
    assert "Related article text that should not appear in the parsed body." not in article.body
    assert "Subscribe to Canary Media newsletters" not in article.body
    assert "Battery solar energy storage units at a solar and battery storage plant." not in article.body


def test_default_targets_match_curated_live_vertical_catalog() -> None:
    targets = CanaryMediaProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "grid-edge",
        "energy-storage",
        "solar",
        "electrification",
        "transportation",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/articles/grid-edge"},
        {"path": "/articles/energy-storage"},
        {"path": "/articles/solar"},
        {"path": "/articles/electrification"},
        {"path": "/articles/transportation"},
    ]
    assert [target.target_kind for target in targets] == ["topic"] * 5
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/canarymedia_listing_grid_edge.html").read_text(encoding="utf-8")

    class StubProvider(CanaryMediaProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            assert url == "https://www.canarymedia.com/articles/grid-edge"
            return html

    target = ProviderTarget(
        provider_id="canarymedia",
        target_key="grid-edge",
        target_kind="topic",
        label="Grid Edge",
        payload={"path": "/articles/grid-edge"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=3)

    assert [
        (candidate.article_id, candidate.provider_article_id, candidate.category)
        for candidate in candidates
    ] == [
        (
            "canarymedia:articles/utilities/as-californians-electrify-tech-prevent-grid-overload",
            "articles/utilities/as-californians-electrify-tech-prevent-grid-overload",
            "Grid Edge",
        ),
        (
            "canarymedia:articles/grid-edge/winter-storm-fern-grid-renewables-gas",
            "articles/grid-edge/winter-storm-fern-grid-renewables-gas",
            "Grid Edge",
        ),
        (
            "canarymedia:articles/transportation/plug-more-evs-into-grid-report",
            "articles/transportation/plug-more-evs-into-grid-report",
            "Grid Edge",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/canarymedia_article_grid_storage_goal.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(CanaryMediaProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="canarymedia:articles/energy-storage/grid-storage-industry-crushes-2025-goal",
        provider_id="canarymedia",
        provider_article_id="articles/energy-storage/grid-storage-industry-crushes-2025-goal",
        url="https://www.canarymedia.com/articles/energy-storage/grid-storage-industry-crushes-2025-goal",
        category="Energy Storage",
    )

    article = StubProvider().fetch_article(candidate)

    assert (
        article.article_id
        == "canarymedia:articles/energy-storage/grid-storage-industry-crushes-2025-goal"
    )
    assert article.provider_id == "canarymedia"
    assert (
        article.provider_article_id
        == "articles/energy-storage/grid-storage-industry-crushes-2025-goal"
    )
    assert article.title == "The grid storage industry set a wild goal for 2025 - and then crushed it"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://www.canarymedia.com/articles/energy-storage/grid-storage-industry-crushes-2025-goal?utm_source=rss#top"
    )

    assert (
        url
        == "https://www.canarymedia.com/articles/energy-storage/grid-storage-industry-crushes-2025-goal"
    )
    assert normalize_target_path("articles/grid-edge/") == "/articles/grid-edge"
    assert is_article_url(url) is True
    assert is_article_url("https://www.canarymedia.com/articles/grid-edge") is False
    assert is_article_url("https://www.canarymedia.com/articles/grid-edge/p2") is False
    assert is_article_url("https://www.canarymedia.com/articles/sponsored/brought-to-you") is False
    assert is_article_url("https://energy.canarymedia.com/bridging-the-gap") is False
    assert article_id_from_url(url) == "articles/energy-storage/grid-storage-industry-crushes-2025-goal"


def test_registry_includes_canarymedia_provider() -> None:
    registry = build_provider_registry()

    assert "canarymedia" in registry
    assert registry["canarymedia"].display_name == "Canary Media"
    assert CANARYMEDIA_ROOT == "https://www.canarymedia.com"
