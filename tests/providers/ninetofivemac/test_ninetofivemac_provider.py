from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.ninetofivemac import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    NINE_TO_FIVE_MAC_ROOT,
    NineToFiveMacProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_native_written_candidates() -> None:
    html = Path("tests/fixtures/ninetofivemac_listing_iphone.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "iPhone")

    assert [candidate.article_id for candidate in candidates] == [
        "2026/04/03/this-interactive-timeline-shows-every-iphone-size-color-spec-and-model-ever-released",
        "2026/04/03/the-weather-channels-storm-radar-app-lets-you-build-your-own-ai-weather-presenter",
        "2026/04/02/ios-26-5-release-date-heres-when-to-expect-new-iphone-features",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/ninetofivemac_article_app_store_ai_takedowns.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns",
        provider_id="9to5mac",
        provider_article_id="2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns",
        url="https://9to5mac.com/2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns/",
        category="App Store",
    )

    article = parse_article_html(html, candidate)

    assert article.url == candidate.url
    assert article.title == "Developer behind controversial AI apps sues Apple over App Store takedowns"
    assert article.author == "Marcus Mendes"
    assert article.published_at is not None
    assert "Ex-Human, the developer behind Botify and Photify AI" in article.body
    assert "Developer seeks injunction against bans" in article.body
    assert "Apple’s actions caused irreparable harm to the business." in article.body
    assert "FTC: We use income earning auto affiliate links." not in article.body
    assert "You’re reading 9to5Mac" not in article.body
    assert "Worth checking out on Amazon" not in article.body


def test_parse_article_html_handles_malformed_date() -> None:
    html = """
    <html>
    <head>
        <meta property="og:title" content="Test Article">
        <meta property="article:published_time" content="not-a-date">
    </head>
    <body>
        <div id="content">
            <h1>Test Article</h1>
            <div class="container med post-content">
                <p>Article body.</p>
            </div>
        </div>
    </body>
    </html>
    """
    candidate = SectionCandidate(
        article_id="2024/01/01/test-article",
        provider_id="9to5mac",
        provider_article_id="2024/01/01/test-article",
        url="https://9to5mac.com/2024/01/01/test-article/",
        category="Test",
    )

    article = parse_article_html(html, candidate)

    assert article.published_at is None


def test_parse_article_html_cleans_site_suffix_from_meta_title() -> None:
    html = """
    <html>
    <head>
        <meta property="og:title" content="Test Article - 9to5Mac">
    </head>
    <body>
        <div id="content">
            <div class="container med post-content">
                <p>Article body.</p>
            </div>
        </div>
    </body>
    </html>
    """
    candidate = SectionCandidate(
        article_id="2024/01/01/test-article",
        provider_id="9to5mac",
        provider_article_id="2024/01/01/test-article",
        url="https://9to5mac.com/2024/01/01/test-article/",
        category="Test",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Test Article"


def test_parse_section_html_keeps_google_only_podcast_patterns_site_specific() -> None:
    html = """
    <html>
    <body>
        <main>
            <div id="posts">
                <a class="article__title-link" href="https://9to5mac.com/2026/04/01/pixelated-5-launch-event/">
                    Pixelated 5: Launch Event Recap
                </a>
            </div>
        </main>
    </body>
    </html>
    """

    candidates = parse_section_html(html, "Test")

    assert [candidate.article_id for candidate in candidates] == [
        "2026/04/01/pixelated-5-launch-event"
    ]


def test_discover_targets_returns_static_catalog() -> None:
    provider = NineToFiveMacProvider()

    default_targets = provider.default_targets()
    discovered_targets = provider.discover_targets()

    assert [target.target_key for target in discovered_targets] == [
        target.target_key for target in default_targets
    ]


def test_default_targets_match_curated_catalog() -> None:
    targets = NineToFiveMacProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "latest",
        "iphone",
        "mac",
        "ipad",
        "apple-watch",
        "vision-pro",
        "apple-tv",
        "airpods",
        "homekit",
        "reviews",
        "how-to",
        "app-store",
        "apple-music",
        "carplay",
        "siri",
        "apple-silicon",
        "apple-arcade",
        "aapl",
    ]
    assert [target.target_kind for target in targets] == ["category"] * len(targets)
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates() -> None:
    html = Path("tests/fixtures/ninetofivemac_listing_iphone.html").read_text(encoding="utf-8")

    class StubProvider(NineToFiveMacProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            assert url == "https://9to5mac.com/guides/iphone/"
            return html

    target = ProviderTarget(
        provider_id="9to5mac",
        target_key="iphone",
        target_kind="category",
        label="iPhone",
        payload={"path": "/guides/iphone/"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=10)

    assert [
        (candidate.article_id, candidate.provider_article_id, candidate.category)
        for candidate in candidates
    ] == [
        (
            "9to5mac:2026/04/03/this-interactive-timeline-shows-every-iphone-size-color-spec-and-model-ever-released",
            "2026/04/03/this-interactive-timeline-shows-every-iphone-size-color-spec-and-model-ever-released",
            "iPhone",
        ),
        (
            "9to5mac:2026/04/03/the-weather-channels-storm-radar-app-lets-you-build-your-own-ai-weather-presenter",
            "2026/04/03/the-weather-channels-storm-radar-app-lets-you-build-your-own-ai-weather-presenter",
            "iPhone",
        ),
        (
            "9to5mac:2026/04/02/ios-26-5-release-date-heres-when-to-expect-new-iphone-features",
            "2026/04/02/ios-26-5-release-date-heres-when-to-expect-new-iphone-features",
            "iPhone",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/ninetofivemac_article_app_store_ai_takedowns.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(NineToFiveMacProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="9to5mac:2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns",
        provider_id="9to5mac",
        provider_article_id="2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns",
        url="https://9to5mac.com/2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns/",
        category="App Store",
    )

    article = StubProvider().fetch_article(candidate)

    assert (
        article.article_id
        == "9to5mac:2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns"
    )
    assert article.provider_id == "9to5mac"
    assert (
        article.provider_article_id
        == "2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns"
    )
    assert article.title == "Developer behind controversial AI apps sues Apple over App Store takedowns"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    article_url = normalize_url(
        "https://www.9to5mac.com/2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns/?extended-comments=1#comments"
    )

    assert (
        article_url
        == "https://9to5mac.com/2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns/"
    )
    assert normalize_target_path("guides/iphone") == "/guides/iphone/"
    assert normalize_target_path("/") == "/"
    assert is_article_url(article_url) is True
    assert is_article_url("https://9to5mac.com/guides/iphone/") is False
    assert is_article_url("https://9to5mac.com/2026/04/02/happy-hour-584/") is True
    assert (
        is_article_url("https://9to5google.com/2026/04/03/pixel-buds-a-series-update-2/") is False
    )
    assert (
        article_id_from_url(article_url)
        == "2026/04/03/developer-behind-controversial-ai-apps-sues-apple-over-app-store-takedowns"
    )


def test_registry_includes_ninetofivemac_provider() -> None:
    registry = build_provider_registry()

    assert "9to5mac" in registry
    assert registry["9to5mac"].display_name == "9to5Mac"
    assert NINE_TO_FIVE_MAC_ROOT == "https://9to5mac.com"
