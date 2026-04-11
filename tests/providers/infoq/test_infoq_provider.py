from __future__ import annotations

from copy import copy
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.infoq import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    INFOQ_ROOT,
    InfoQProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/infoq_listing_cloud_architecture.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(_with_duplicate_card(html), "Cloud Architecture")

    assert [candidate.article_id for candidate in candidates[:6]] == [
        "news/2026/03/cloudflare-custom-regions",
        "news/2026/03/uber-mysql-uptime-consensus",
        "news/2026/02/amazon-key-event-driven-platform",
        "news/2026/02/uber-pull-based-opensearch",
        "news/2025/11/disaggregated-systems-qcon",
        "news/2025/11/azure-afd-control-plane-failure",
    ]
    assert "articles/configuration-control-plane" in {
        candidate.article_id for candidate in candidates
    }
    assert len({candidate.article_id for candidate in candidates}) == len(candidates)
    assert all(
        not candidate.article_id.startswith(("podcasts/", "presentations/", "minibooks/"))
        for candidate in candidates
    )


def test_parse_article_html_extracts_article_body_metadata() -> None:
    html = Path("tests/fixtures/infoq_article_configuration_control_plane.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="articles/configuration-control-plane",
        provider_id="infoq",
        provider_article_id="articles/configuration-control-plane",
        url="https://www.infoq.com/articles/configuration-control-plane/",
        category="Cloud Architecture",
    )

    article = parse_article_html(html, candidate)

    assert article.url == "https://www.infoq.com/articles/configuration-control-plane/"
    assert article.title == "Configuration as a Control Plane: Designing for Safety and Reliability at Scale"
    assert article.author == "Karthiek Maralla"
    assert article.published_at is not None
    assert "configuration is no longer merely an operational concern" in article.body
    assert "A Condensed History: How Configuration Management Evolved" in article.body
    assert "About the Author" not in article.body
    assert "Show more" not in article.body
    assert "For full size image click here" not in article.body


def test_parse_article_html_extracts_news_body_metadata() -> None:
    html = Path("tests/fixtures/infoq_news_cloudflare_custom_regions.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="news/2026/03/cloudflare-custom-regions",
        provider_id="infoq",
        provider_article_id="news/2026/03/cloudflare-custom-regions",
        url="https://www.infoq.com/news/2026/03/cloudflare-custom-regions/",
        category="Cloud Architecture",
    )

    article = parse_article_html(html, candidate)

    assert article.url == "https://www.infoq.com/news/2026/03/cloudflare-custom-regions/"
    assert (
        article.title
        == '"Pick and Mix" Custom Regions: Cloudflare Introduces Fine-Grained Data Residency Control'
    )
    assert article.author == "Renato Losio"
    assert article.published_at is not None
    assert "Cloudflare recently introduced Custom Regions" in article.body
    assert "Custom Regions can be defined using arbitrary geographic groupings." in article.body
    assert "About the Author" not in article.body
    assert "Source: Cloudflare blog" not in article.body


def test_default_targets_match_curated_live_topic_catalog() -> None:
    targets = InfoQProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "software-architecture",
        "cloud-architecture",
        "devops",
        "ai-ml-data-engineering",
        "java",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/architecture/"},
        {"path": "/cloud-architecture/"},
        {"path": "/devops/"},
        {"path": "/ai-ml-data-eng/"},
        {"path": "/java/"},
    ]
    assert [target.target_kind for target in targets] == ["topic"] * 5
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/infoq_listing_cloud_architecture.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(InfoQProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            assert url == "https://www.infoq.com/cloud-architecture/"
            return html

    target = ProviderTarget(
        provider_id="infoq",
        target_key="cloud-architecture",
        target_kind="topic",
        label="Cloud Architecture",
        payload={"path": "/cloud-architecture/"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=15)

    assert [
        (candidate.article_id, candidate.provider_article_id, candidate.category)
        for candidate in candidates[:5]
    ] == [
        (
            "infoq:news/2026/03/cloudflare-custom-regions",
            "news/2026/03/cloudflare-custom-regions",
            "Cloud Architecture",
        ),
        (
            "infoq:news/2026/03/uber-mysql-uptime-consensus",
            "news/2026/03/uber-mysql-uptime-consensus",
            "Cloud Architecture",
        ),
        (
            "infoq:news/2026/02/amazon-key-event-driven-platform",
            "news/2026/02/amazon-key-event-driven-platform",
            "Cloud Architecture",
        ),
        (
            "infoq:news/2026/02/uber-pull-based-opensearch",
            "news/2026/02/uber-pull-based-opensearch",
            "Cloud Architecture",
        ),
        (
            "infoq:news/2025/11/disaggregated-systems-qcon",
            "news/2025/11/disaggregated-systems-qcon",
            "Cloud Architecture",
        ),
    ]
    assert candidates[13].article_id == "infoq:articles/configuration-control-plane"
    assert candidates[13].provider_article_id == "articles/configuration-control-plane"


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/infoq_article_configuration_control_plane.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(InfoQProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="infoq:articles/configuration-control-plane",
        provider_id="infoq",
        provider_article_id="articles/configuration-control-plane",
        url="https://www.infoq.com/articles/configuration-control-plane/",
        category="Cloud Architecture",
    )

    article = StubProvider().fetch_article(candidate)

    assert article.article_id == "infoq:articles/configuration-control-plane"
    assert article.provider_id == "infoq"
    assert article.provider_article_id == "articles/configuration-control-plane"
    assert article.title == "Configuration as a Control Plane: Designing for Safety and Reliability at Scale"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    news_url = normalize_url(
        "http://infoq.com/news/2026/03/cloudflare-custom-regions?utm_source=rss#top"
    )
    article_url = normalize_url("https://infoq.com/articles/configuration-control-plane")

    assert news_url == "https://www.infoq.com/news/2026/03/cloudflare-custom-regions/"
    assert article_url == "https://www.infoq.com/articles/configuration-control-plane/"
    assert normalize_target_path("cloud-architecture") == "/cloud-architecture/"
    assert is_article_url(news_url) is True
    assert is_article_url(article_url) is True
    assert is_article_url("https://www.infoq.com/podcasts/release-software-jreleaser/") is False
    assert (
        is_article_url("https://www.infoq.com/presentations/slack-cellular-architecture/")
        is False
    )
    assert article_id_from_url(news_url) == "news/2026/03/cloudflare-custom-regions"
    assert article_id_from_url(article_url) == "articles/configuration-control-plane"


def test_registry_includes_infoq_provider() -> None:
    registry = build_provider_registry()

    assert "infoq" in registry
    assert registry["infoq"].display_name == "InfoQ"
    assert INFOQ_ROOT == "https://www.infoq.com"


def _with_duplicate_card(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    card = soup.select_one('li[data-path="/news/2026/03/cloudflare-custom-regions"]')
    if not isinstance(card, Tag) or not isinstance(card.parent, Tag):
        return html
    card.parent.append(copy(card))
    return str(soup)
