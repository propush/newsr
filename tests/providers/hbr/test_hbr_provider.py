from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.hbr import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    HBR_ROOT,
    HBRProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_mixed_format_cards() -> None:
    html = Path("tests/fixtures/hbr_listing_leadership.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "Leadership")

    assert [candidate.article_id for candidate in candidates[:5]] == [
        "2026/03/how-leaders-can-build-a-high-agency-culture",
        "2026/03/how-to-convince-others-to-trust-your-instincts",
        "2026/03/leaders-feel-their-agency-eroding-and-theyre-starting-to-withdraw",
        "2026/03/how-senior-leaders-can-build-their-influence",
        "2026/03/will-the-iran-war-deliver-a-long-predicted-u-s-recession",
    ]
    assert "2026/03/bill-ready-hbre-live" not in {
        candidate.article_id for candidate in candidates
    }
    assert "2026/05/what-companies-can-learn-from-their-biggest-fans" not in {
        candidate.article_id for candidate in candidates
    }
    assert "2026/03/how-to-navigate-through-the-fog" not in {
        candidate.article_id for candidate in candidates
    }


def test_parse_article_html_extracts_body_metadata_from_next_data() -> None:
    html = Path("tests/fixtures/hbr_article_digital.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="2026/03/how-to-convince-others-to-trust-your-instincts",
        provider_id="hbr",
        provider_article_id="2026/03/how-to-convince-others-to-trust-your-instincts",
        url="https://hbr.org/2026/03/how-to-convince-others-to-trust-your-instincts",
        category="Leadership",
    )

    article = parse_article_html(html, candidate)

    assert article.url == "https://hbr.org/2026/03/how-to-convince-others-to-trust-your-instincts"
    assert article.title == "How to Convince Others to Trust Your Instincts"
    assert article.author == "Melody Wilding"
    assert article.published_at is not None
    assert "Your team is finalizing a new strategy during a meeting." in article.body
    assert "The most effective executives integrate data and instinct." in article.body
    assert "Buy copies" not in article.body
    assert "Gift this article" not in article.body


def test_parse_article_html_returns_empty_body_for_unusable_page_shape() -> None:
    html = Path("tests/fixtures/hbr_article_unusable.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="2026/03/unusable-article",
        provider_id="hbr",
        provider_article_id="2026/03/unusable-article",
        url="https://hbr.org/2026/03/unusable-article",
        category="Leadership",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Unusable Article"
    assert article.body == ""


def test_default_targets_match_curated_hbr_catalog() -> None:
    targets = HBRProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "leadership",
        "strategy",
        "innovation",
        "managing-people",
        "managing-yourself",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/topic/subject/leadership"},
        {"path": "/topic/subject/strategy"},
        {"path": "/topic/subject/innovation"},
        {"path": "/topic/subject/managing-people"},
        {"path": "/topic/subject/managing-yourself"},
    ]
    assert [target.target_kind for target in targets] == ["topic"] * 5
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/hbr_listing_leadership.html").read_text(encoding="utf-8")

    class StubProvider(HBRProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    target = ProviderTarget(
        provider_id="hbr",
        target_key="leadership",
        target_kind="topic",
        label="Leadership",
        payload={"path": "/topic/subject/leadership"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=3)

    assert [(candidate.article_id, candidate.provider_article_id, candidate.category) for candidate in candidates] == [
        (
            "hbr:2026/03/how-leaders-can-build-a-high-agency-culture",
            "2026/03/how-leaders-can-build-a-high-agency-culture",
            "Leadership",
        ),
        (
            "hbr:2026/03/how-to-convince-others-to-trust-your-instincts",
            "2026/03/how-to-convince-others-to-trust-your-instincts",
            "Leadership",
        ),
        (
            "hbr:2026/03/leaders-feel-their-agency-eroding-and-theyre-starting-to-withdraw",
            "2026/03/leaders-feel-their-agency-eroding-and-theyre-starting-to-withdraw",
            "Leadership",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/hbr_article_digital.html").read_text(encoding="utf-8")

    class StubProvider(HBRProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="hbr:2026/03/how-to-convince-others-to-trust-your-instincts",
        provider_id="hbr",
        provider_article_id="2026/03/how-to-convince-others-to-trust-your-instincts",
        url="https://hbr.org/2026/03/how-to-convince-others-to-trust-your-instincts",
        category="Leadership",
    )

    article = StubProvider().fetch_article(candidate)

    assert article.article_id == "hbr:2026/03/how-to-convince-others-to-trust-your-instincts"
    assert article.provider_id == "hbr"
    assert article.provider_article_id == "2026/03/how-to-convince-others-to-trust-your-instincts"
    assert article.title == "How to Convince Others to Trust Your Instincts"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://www.hbr.org/2026/03/how-to-convince-others-to-trust-your-instincts?utm_source=test#top"
    )

    assert url == "https://hbr.org/2026/03/how-to-convince-others-to-trust-your-instincts"
    assert normalize_target_path("topic/subject/leadership/") == "/topic/subject/leadership"
    assert is_article_url(url) is True
    assert is_article_url("https://hbr.org/topic/subject/leadership") is False
    assert is_article_url("https://hbr.org/podcasts/ideacast/example") is False
    assert is_article_url("https://store.hbr.org/product/example") is False
    assert article_id_from_url(url) == "2026/03/how-to-convince-others-to-trust-your-instincts"


def test_registry_includes_hbr_provider() -> None:
    registry = build_provider_registry()

    assert "hbr" in registry
    assert registry["hbr"].display_name == "Harvard Business Review"
    assert HBR_ROOT == "https://hbr.org"
