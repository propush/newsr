from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.marketingdive import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    MARKETINGDIVE_ROOT,
    MarketingDiveProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/marketingdive_listing_social_media.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(html, "Social Media")

    assert [candidate.article_id for candidate in candidates] == [
        "news/reddit-expands-conversation-ads/743210",
        "news/tiktok-shops-us-growth/743245",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/marketingdive_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="news/reddit-expands-conversation-ads/743210",
        provider_id="marketingdive",
        provider_article_id="news/reddit-expands-conversation-ads/743210",
        url="https://www.marketingdive.com/news/reddit-expands-conversation-ads/743210/",
        category="Social Media",
    )

    article = parse_article_html(html, candidate)

    assert article.url == "https://www.marketingdive.com/news/reddit-expands-conversation-ads/743210/"
    assert article.title == "Reddit expands conversation ads with new controls"
    assert article.author == "Chris Kelly"
    assert article.published_at is not None
    assert "Reddit is giving brands more control" in article.body
    assert "creator partnerships" in article.body
    assert "Subscribe to Marketing Dive" not in article.body
    assert "Read more: Related coverage" not in article.body


def test_default_targets_match_curated_marketing_dive_catalog() -> None:
    targets = MarketingDiveProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "brand-strategy",
        "mobile",
        "creative",
        "social-media",
        "video",
        "agencies",
        "data-analytics",
        "influencer",
        "marketing",
        "ad-tech",
        "cmo-corner",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/topic/brand-strategy/"},
        {"path": "/topic/mobile-marketing/"},
        {"path": "/topic/creative/"},
        {"path": "/topic/social-media/"},
        {"path": "/topic/video/"},
        {"path": "/topic/agencies/"},
        {"path": "/topic/analytics/"},
        {"path": "/topic/influencer-marketing/"},
        {"path": "/"},
        {"path": "/topic/marketing-tech/"},
        {"path": "/topic/cmo-corner/"},
    ]
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/marketingdive_listing_social_media.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(MarketingDiveProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    target = ProviderTarget(
        provider_id="marketingdive",
        target_key="social-media",
        target_kind="category",
        label="Social Media",
        payload={"path": "/topic/social-media/"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=5)

    assert [(candidate.article_id, candidate.provider_article_id, candidate.category) for candidate in candidates] == [
        (
            "marketingdive:news/reddit-expands-conversation-ads/743210",
            "news/reddit-expands-conversation-ads/743210",
            "Social Media",
        ),
        (
            "marketingdive:news/tiktok-shops-us-growth/743245",
            "news/tiktok-shops-us-growth/743245",
            "Social Media",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/marketingdive_article.html").read_text(encoding="utf-8")

    class StubProvider(MarketingDiveProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="marketingdive:news/reddit-expands-conversation-ads/743210",
        provider_id="marketingdive",
        provider_article_id="news/reddit-expands-conversation-ads/743210",
        url="https://www.marketingdive.com/news/reddit-expands-conversation-ads/743210/",
        category="Social Media",
    )

    article = StubProvider().fetch_article(candidate)

    assert article.article_id == "marketingdive:news/reddit-expands-conversation-ads/743210"
    assert article.provider_id == "marketingdive"
    assert article.provider_article_id == "news/reddit-expands-conversation-ads/743210"
    assert article.title == "Reddit expands conversation ads with new controls"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://www.marketingdive.com/news/reddit-expands-conversation-ads/743210?utm_source=test#top"
    )

    assert url == "https://www.marketingdive.com/news/reddit-expands-conversation-ads/743210/"
    assert normalize_target_path("topic/social-media") == "/topic/social-media/"
    assert normalize_target_path("/") == "/"
    assert is_article_url(url) is True
    assert is_article_url("https://www.marketingdive.com/topic/social-media/") is False
    assert is_article_url("https://www.marketingdive.com/events/brand-week/") is False
    assert is_article_url("https://resources.industrydive.com/webinar/example") is False
    assert article_id_from_url(url) == "news/reddit-expands-conversation-ads/743210"


def test_registry_includes_marketingdive_provider() -> None:
    registry = build_provider_registry()

    assert "marketingdive" in registry
    assert registry["marketingdive"].display_name == "Marketing Dive"
    assert MARKETINGDIVE_ROOT == "https://www.marketingdive.com"
