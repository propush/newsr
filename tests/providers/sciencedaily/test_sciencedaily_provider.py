from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.registry import build_provider_registry
from newsr.providers.sciencedaily import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    SCIENCEDAILY_ROOT,
    ScienceDailyProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/sciencedaily_listing_computers_math.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(html, "Computers & Math")

    assert [candidate.article_id for candidate in candidates[:6]] == [
        "releases/2026/03/260328043603",
        "releases/2026/03/260328212132",
        "releases/2026/03/260326075614",
        "releases/2026/03/260326064200",
        "releases/2026/03/260326011452",
        "releases/2026/03/260324024249",
    ]
    assert len({candidate.article_id for candidate in candidates}) == len(candidates)


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/sciencedaily_article_chip_flaws.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="releases/2026/03/260305182657",
        provider_id="sciencedaily",
        provider_article_id="releases/2026/03/260305182657",
        url="https://www.sciencedaily.com/releases/2026/03/260305182657.htm",
        category="Computers & Math",
    )

    article = parse_article_html(html, candidate)

    assert article.url == "https://www.sciencedaily.com/releases/2026/03/260305182657.htm"
    assert article.title == "Scientists finally see the atomic flaws hiding inside computer chips"
    assert article.author == "Cornell University"
    assert article.published_at is not None
    assert "Researchers at Cornell University have developed a powerful imaging technique" in article.body
    assert "The new imaging technique was developed through a collaboration with Taiwan Semiconductor Manufacturing Company" in article.body
    assert "RELATED TOPICS" not in article.body
    assert "Story Source:" not in article.body
    assert "Credit: Cornell University" not in article.body


def test_discover_targets_returns_static_catalog() -> None:
    provider = ScienceDailyProvider()

    default_targets = provider.default_targets()
    discovered_targets = provider.discover_targets()

    assert [target.target_key for target in discovered_targets] == [
        target.target_key for target in default_targets
    ]


def test_default_targets_match_live_sciencedaily_catalog() -> None:
    targets = ScienceDailyProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "health_medicine",
        "computers_math",
        "earth_climate",
        "mind_brain",
        "matter_energy",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/news/health_medicine/"},
        {"path": "/news/computers_math/"},
        {"path": "/news/earth_climate/"},
        {"path": "/news/mind_brain/"},
        {"path": "/news/matter_energy/"},
    ]
    assert [target.target_kind for target in targets] == ["category"] * 5
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/sciencedaily_listing_computers_math.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(ScienceDailyProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            assert url == "https://www.sciencedaily.com/news/computers_math/"
            return html

    target = ProviderTarget(
        provider_id="sciencedaily",
        target_key="computers_math",
        target_kind="category",
        label="Computers & Math",
        payload={"path": "/news/computers_math/"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=4)

    assert [
        (candidate.article_id, candidate.provider_article_id, candidate.category)
        for candidate in candidates
    ] == [
        (
            "sciencedaily:releases/2026/03/260328043603",
            "releases/2026/03/260328043603",
            "Computers & Math",
        ),
        (
            "sciencedaily:releases/2026/03/260328212132",
            "releases/2026/03/260328212132",
            "Computers & Math",
        ),
        (
            "sciencedaily:releases/2026/03/260326075614",
            "releases/2026/03/260326075614",
            "Computers & Math",
        ),
        (
            "sciencedaily:releases/2026/03/260326064200",
            "releases/2026/03/260326064200",
            "Computers & Math",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/sciencedaily_article_chip_flaws.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(ScienceDailyProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="sciencedaily:releases/2026/03/260305182657",
        provider_id="sciencedaily",
        provider_article_id="releases/2026/03/260305182657",
        url="https://www.sciencedaily.com/releases/2026/03/260305182657.htm",
        category="Computers & Math",
    )

    article = StubProvider().fetch_article(candidate)

    assert article.article_id == "sciencedaily:releases/2026/03/260305182657"
    assert article.provider_id == "sciencedaily"
    assert article.provider_article_id == "releases/2026/03/260305182657"
    assert article.title == "Scientists finally see the atomic flaws hiding inside computer chips"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://sciencedaily.com/releases/2026/03/260305182657.htm?utm_source=rss#top"
    )

    assert url == "https://www.sciencedaily.com/releases/2026/03/260305182657.htm"
    assert normalize_target_path("news/computers_math") == "/news/computers_math/"
    assert is_article_url(url) is True
    assert is_article_url("https://www.sciencedaily.com/news/computers_math/") is False
    assert is_article_url("https://www.sciencedaily.com/breaking/") is False
    assert is_article_url("https://example.com/releases/2026/03/260305182657.htm") is False
    assert article_id_from_url(url) == "releases/2026/03/260305182657"


def test_registry_includes_sciencedaily_provider() -> None:
    registry = build_provider_registry()

    assert "sciencedaily" in registry
    assert registry["sciencedaily"].display_name == "ScienceDaily"
    assert SCIENCEDAILY_ROOT == "https://www.sciencedaily.com"
