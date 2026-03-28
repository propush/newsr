from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.deloitteinsights import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    DELOITTE_ROOT,
    DeloitteInsightsProvider,
    article_id_from_url,
    is_article_url,
    is_research_hub_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_search_response,
)
from newsr.providers.registry import build_provider_registry


def test_parse_search_response_extracts_unique_candidates_and_rejects_non_articles() -> None:
    payload = Path("tests/fixtures/deloitteinsights_search_business_strategy_growth.json").read_text(
        encoding="utf-8"
    )

    candidates = parse_search_response(payload, "Strategy")

    assert [candidate.article_id for candidate in candidates] == [
        "us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
        "us/en/insights/topics/technology-management/tech-trends/2024/tech-trends-future-of-engineering-in-technology.html",
        "us/en/insights/research-centers/economics.html",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/deloitteinsights_article_tracking_financial_stress_metrics.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
        provider_id="deloitteinsights",
        provider_article_id="us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
        url="https://www.deloitte.com/us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
        category="Strategy",
    )

    article = parse_article_html(html, candidate)

    assert (
        article.url
        == "https://www.deloitte.com/us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html"
    )
    assert article.title == "The importance of sharing success—and stress—metrics"
    assert article.author == "Jo Mitchell-Marais, Gregor Adrian Böttcher"
    assert article.published_at is not None
    assert "Author, commentator, and policy analyst Michele Wucker coined the term" in article.body
    assert "the proactive tracking of indicators of financial stress is critically important" in article.body
    assert "To access the research report, visit" not in article.body
    assert "Cover image by" not in article.body


def test_parse_article_html_extracts_research_hub_intro_metadata() -> None:
    html = Path("tests/fixtures/deloitteinsights_research_hub_economics.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="us/en/insights/research-centers/economics.html",
        provider_id="deloitteinsights",
        provider_article_id="us/en/insights/research-centers/economics.html",
        url="https://www.deloitte.com/us/en/insights/research-centers/economics.html",
        category="Economics",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Deloitte Global Economics Research Center"
    assert article.author is None
    assert article.published_at is None
    assert "Economic forces shape our personal, business, and political situations" in article.body
    assert "Learn about our services" not in article.body
    assert "Looking to stay on top of the latest news and trends" not in article.body


def test_parse_article_html_aggregates_multi_block_body_content() -> None:
    html = Path(
        "tests/fixtures/deloitteinsights_article_thriving_in_midst_leadership_tension_uncertainty.html"
    ).read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="us/en/insights/focus/human-capital-trends/2025/thriving-in-midst-leadership-tension-uncertainty.html",
        provider_id="deloitteinsights",
        provider_article_id="us/en/insights/focus/human-capital-trends/2025/thriving-in-midst-leadership-tension-uncertainty.html",
        url="https://www.deloitte.com/us/en/insights/focus/human-capital-trends/2025/thriving-in-midst-leadership-tension-uncertainty.html",
        category="Workforce",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Turning tensions into triumphs: Helping leaders transform uncertainty into opportunity"
    assert "Should we consider going bossless?" in article.body
    assert "These are the fundamental tensions (figure 1) that organizational leaders everywhere are currently facing." in article.body
    assert "To be a leader is to decide" in article.body
    assert "Key questions, tensions, and decisions for leaders in the 2025 trends" in article.body
    assert "Table of contents" not in article.body


def test_discover_targets_returns_static_catalog() -> None:
    provider = DeloitteInsightsProvider()

    default_targets = provider.default_targets()
    discovered_targets = provider.discover_targets()

    assert [target.target_key for target in discovered_targets] == [
        target.target_key for target in default_targets
    ]


def test_default_targets_match_curated_live_topic_catalog() -> None:
    targets = DeloitteInsightsProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "business-strategy-growth",
        "technology-management",
        "talent",
        "operations",
        "economy",
    ]
    assert [target.payload for target in targets] == [
        {
            "path": "/us/en/insights/topics/business-strategy-growth.html",
            "search_tag": "Strategy",
        },
        {
            "path": "/us/en/insights/topics/technology-management.html",
            "search_tag": "Technology management",
        },
        {
            "path": "/us/en/insights/topics/talent.html",
            "search_tag": "Talent",
        },
        {
            "path": "/us/en/insights/topics/operations.html",
            "search_tag": "Operations",
        },
        {
            "path": "/us/en/insights/topics/economy.html",
            "search_tag": "Economics",
        },
    ]
    assert [target.target_kind for target in targets] == ["topic"] * 5
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    payload = Path("tests/fixtures/deloitteinsights_search_business_strategy_growth.json").read_text(
        encoding="utf-8"
    )

    class StubProvider(DeloitteInsightsProvider):
        @staticmethod
        def _read_search_results(search_tag: str, limit: int, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            assert search_tag == "Strategy"
            return payload

    target = ProviderTarget(
        provider_id="deloitteinsights",
        target_key="business-strategy-growth",
        target_kind="topic",
        label="Strategy",
        payload={
            "path": "/us/en/insights/topics/business-strategy-growth.html",
            "search_tag": "Strategy",
        },
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=3)

    assert [
        (candidate.article_id, candidate.provider_article_id, candidate.category)
        for candidate in candidates
    ] == [
        (
            "deloitteinsights:us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
            "us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
            "Strategy",
        ),
        (
            "deloitteinsights:us/en/insights/topics/technology-management/tech-trends/2024/tech-trends-future-of-engineering-in-technology.html",
            "us/en/insights/topics/technology-management/tech-trends/2024/tech-trends-future-of-engineering-in-technology.html",
            "Strategy",
        ),
        (
            "deloitteinsights:us/en/insights/research-centers/economics.html",
            "us/en/insights/research-centers/economics.html",
            "Strategy",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/deloitteinsights_article_tracking_financial_stress_metrics.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(DeloitteInsightsProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="deloitteinsights:us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
        provider_id="deloitteinsights",
        provider_article_id="us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
        url="https://www.deloitte.com/us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html",
        category="Strategy",
    )

    article = StubProvider().fetch_article(candidate)

    assert (
        article.article_id
        == "deloitteinsights:us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html"
    )
    assert article.provider_id == "deloitteinsights"
    assert (
        article.provider_article_id
        == "us/en/insights/topics/business-strategy-growth/tracking-financial-stress-metrics.html"
    )
    assert article.title == "The importance of sharing success—and stress—metrics"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://www.deloitte.com/us/en/insights/topics/technology-management/tech-trends/2024/tech-trends-future-of-engineering-in-technology.html.html?icid=test#top"
    )

    assert (
        url
        == "https://www.deloitte.com/us/en/insights/topics/technology-management/tech-trends/2024/tech-trends-future-of-engineering-in-technology.html"
    )
    assert normalize_target_path("us/en/insights/topics/business-strategy-growth.html") == (
        "/us/en/insights/topics/business-strategy-growth.html"
    )
    assert is_article_url(url) is True
    assert is_article_url("https://www.deloitte.com/us/en/insights/multimedia/videos.html") is False
    assert is_research_hub_url("https://www.deloitte.com/us/en/insights/research-centers/economics.html") is True
    assert (
        article_id_from_url(url)
        == "us/en/insights/topics/technology-management/tech-trends/2024/tech-trends-future-of-engineering-in-technology.html"
    )


def test_registry_includes_deloitteinsights_provider() -> None:
    registry = build_provider_registry()

    assert "deloitteinsights" in registry
    assert registry["deloitteinsights"].display_name == "Deloitte Insights"
    assert DELOITTE_ROOT == "https://www.deloitte.com"
