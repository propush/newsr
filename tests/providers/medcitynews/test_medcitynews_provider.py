from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.medcitynews import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    MEDCITYNEWS_ROOT,
    MedCityNewsProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/medcitynews_listing_health_tech.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(html, "Health Tech")

    assert [candidate.article_id for candidate in candidates] == [
        "2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation",
        "2026/03/closing-behavioral-care-gaps-three-ways-providers-and-health-plans-can-reimagine-care",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/medcitynews_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation",
        provider_id="medcitynews",
        provider_article_id="2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation",
        url="https://medcitynews.com/2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation/",
        category="Health Tech",
    )

    article = parse_article_html(html, candidate)

    assert (
        article.url
        == "https://medcitynews.com/2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation/"
    )
    assert article.title == "UnitedHealthcare Unveils AI Companion to Improve Navigation"
    assert article.author == "Marissa Plescia"
    assert article.published_at is not None
    assert "UnitedHealthcare launched a new AI companion named Avery" in article.body
    assert "Avery also provides a summary of the issue" in article.body
    assert "Sponsored promo text" not in article.body
    assert "MedCity News Daily Newsletter" not in article.body
    assert "More from MedCity News" not in article.body
    assert "Photo: Example Credit" not in article.body


def test_default_targets_match_curated_live_channel_catalog() -> None:
    targets = MedCityNewsProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "health-tech",
        "biopharma",
        "medical-devices-and-diagnostics",
        "consumer-employer",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/category/channel/health-tech/"},
        {"path": "/category/channel/biopharma/"},
        {"path": "/category/channel/medical-devices-and-diagnostics/"},
        {"path": "/category/channel/consumer-employer/"},
    ]
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/medcitynews_listing_health_tech.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(MedCityNewsProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    target = ProviderTarget(
        provider_id="medcitynews",
        target_key="health-tech",
        target_kind="category",
        label="Health Tech",
        payload={"path": "/category/channel/health-tech/"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=5)

    assert [
        (candidate.article_id, candidate.provider_article_id, candidate.category)
        for candidate in candidates
    ] == [
        (
            "medcitynews:2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation",
            "2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation",
            "Health Tech",
        ),
        (
            "medcitynews:2026/03/closing-behavioral-care-gaps-three-ways-providers-and-health-plans-can-reimagine-care",
            "2026/03/closing-behavioral-care-gaps-three-ways-providers-and-health-plans-can-reimagine-care",
            "Health Tech",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/medcitynews_article.html").read_text(encoding="utf-8")

    class StubProvider(MedCityNewsProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="medcitynews:2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation",
        provider_id="medcitynews",
        provider_article_id="2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation",
        url="https://medcitynews.com/2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation/",
        category="Health Tech",
    )

    article = StubProvider().fetch_article(candidate)

    assert (
        article.article_id
        == "medcitynews:2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation"
    )
    assert article.provider_id == "medcitynews"
    assert (
        article.provider_article_id
        == "2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation"
    )
    assert article.title == "UnitedHealthcare Unveils AI Companion to Improve Navigation"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://medcitynews.com/2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation/?utm_source=test#top"
    )

    assert (
        url
        == "https://medcitynews.com/2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation/"
    )
    assert normalize_target_path("category/channel/health-tech") == "/category/channel/health-tech/"
    assert is_article_url(url) is True
    assert is_article_url("https://medcitynews.com/category/channel/health-tech/") is False
    assert is_article_url("https://medcitynews.com/tag/ai/") is False
    assert is_article_url("https://medcitynews.com/author/mplescia/") is False
    assert is_article_url("https://medcitynews.com/medcity-podcasts/") is False
    assert is_article_url("https://info.medcitynews.com/example-guide") is False
    assert (
        article_id_from_url(url)
        == "2026/03/unitedhealthcare-unveils-ai-companion-to-improve-navigation"
    )


def test_registry_includes_medcitynews_provider() -> None:
    registry = build_provider_registry()

    assert "medcitynews" in registry
    assert registry["medcitynews"].display_name == "MedCity News"
    assert MEDCITYNEWS_ROOT == "https://medcitynews.com"
