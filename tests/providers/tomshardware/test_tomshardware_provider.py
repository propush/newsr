from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.tomshardware import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    TOMSHARDWARE_ROOT,
    TomsHardwareProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/tomshardware_listing_cpus.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "CPUs")

    assert [candidate.article_id for candidate in candidates] == [
        "pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
        "pc-components/cpus/amd-makes-the-flagship-ryzen-9-9950x3d2-official-first-dual-cache-x3d-cpu-arrives-in-april-with-208mb-cache-200w-tdp-promising-modest-performance-gains",
        "reviews/intel-core-ultra-5-250k-plus-review,11111.html",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/tomshardware_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
        provider_id="tomshardware",
        provider_article_id="pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
        url="https://www.tomshardware.com/pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
        category="CPUs",
    )

    article = parse_article_html(html, candidate)

    assert (
        article.url
        == "https://www.tomshardware.com/pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out"
    )
    assert article.title == "Intel confirms rumored Core Ultra 9 290K Plus has been scrapped"
    assert article.author == "Aaron Klotz"
    assert article.published_at is not None
    assert "Intel has confirmed it has scrapped the Core Ultra 9 290K Plus" in article.body
    assert "That would have made the part a difficult sell" in article.body
    assert "affiliate commission" not in article.body
    assert "Article continues below" not in article.body
    assert "Go deeper with TH Premium" not in article.body


def test_default_targets_match_curated_toms_hardware_catalog() -> None:
    targets = TomsHardwareProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "pc-components",
        "cpus",
        "gpus",
        "storage",
        "laptops",
        "desktops",
        "software",
        "artificial-intelligence",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/pc-components"},
        {"path": "/pc-components/cpus"},
        {"path": "/pc-components/gpus"},
        {"path": "/pc-components/storage"},
        {"path": "/laptops/news"},
        {"path": "/desktops"},
        {"path": "/software"},
        {"path": "/tech-industry/artificial-intelligence"},
    ]
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/tomshardware_listing_cpus.html").read_text(encoding="utf-8")

    class StubProvider(TomsHardwareProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    target = ProviderTarget(
        provider_id="tomshardware",
        target_key="cpus",
        target_kind="category",
        label="CPUs",
        payload={"path": "/pc-components/cpus"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=5)

    assert [(candidate.article_id, candidate.provider_article_id, candidate.category) for candidate in candidates] == [
        (
            "tomshardware:pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
            "pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
            "CPUs",
        ),
        (
            "tomshardware:pc-components/cpus/amd-makes-the-flagship-ryzen-9-9950x3d2-official-first-dual-cache-x3d-cpu-arrives-in-april-with-208mb-cache-200w-tdp-promising-modest-performance-gains",
            "pc-components/cpus/amd-makes-the-flagship-ryzen-9-9950x3d2-official-first-dual-cache-x3d-cpu-arrives-in-april-with-208mb-cache-200w-tdp-promising-modest-performance-gains",
            "CPUs",
        ),
        (
            "tomshardware:reviews/intel-core-ultra-5-250k-plus-review,11111.html",
            "reviews/intel-core-ultra-5-250k-plus-review,11111.html",
            "CPUs",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/tomshardware_article.html").read_text(encoding="utf-8")

    class StubProvider(TomsHardwareProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="tomshardware:pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
        provider_id="tomshardware",
        provider_article_id="pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
        url="https://www.tomshardware.com/pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out",
        category="CPUs",
    )

    article = StubProvider().fetch_article(candidate)

    assert (
        article.article_id
        == "tomshardware:pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out"
    )
    assert article.provider_id == "tomshardware"
    assert (
        article.provider_article_id
        == "pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out"
    )
    assert article.title == "Intel confirms rumored Core Ultra 9 290K Plus has been scrapped"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://www.tomshardware.com/pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out?utm_source=test#top"
    )

    assert (
        url
        == "https://www.tomshardware.com/pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out"
    )
    assert normalize_target_path("pc-components/cpus") == "/pc-components/cpus"
    assert is_article_url(url) is True
    assert is_article_url("https://www.tomshardware.com/pc-components/cpus") is False
    assert is_article_url("https://www.tomshardware.com/laptops/news") is False
    assert (
        is_article_url(
            "https://www.tomshardware.com/laptops/news/framework-releases-monthly-update-about-memory-and-storage-pricing-woes"
        )
        is True
    )
    assert is_article_url("https://www.tomshardware.com/desktops") is False
    assert (
        is_article_url(
            "https://www.tomshardware.com/desktops/gaming-pcs/life-support-build-breaking-all-the-rules-to-build-a-productivity-pc-beast"
        )
        is True
    )
    assert is_article_url("https://www.tomshardware.com/software") is False
    assert (
        is_article_url(
            "https://www.tomshardware.com/software/windows/microsoft-and-samsung-scramble-to-fix-a-major-c-drive-lockout-bug-on-galaxy-devices-faulty-galaxy-connect-app-leaves-users-with-limited-recovery-options-following-recent-windows-11-update"
        )
        is True
    )
    assert is_article_url("https://www.tomshardware.com/reviews/best-cpus,3986.html") is False
    assert is_article_url("https://www.tomshardware.com/pc-components/cpus/where-to-buy-intels-core-ultra-5-250k-plus") is True
    assert is_article_url("https://www.tomshardware.com/reviews/intel-core-ultra-5-250k-plus-review,11111.html") is True
    assert (
        article_id_from_url(url)
        == "pc-components/cpus/intel-confirms-rumored-core-ultra-9-290k-plus-has-been-scrapped-potential-core-ultra-9-285ks-special-edition-also-off-the-table-as-arrow-lake-refresh-rolls-out"
    )


def test_registry_includes_tomshardware_provider() -> None:
    registry = build_provider_registry()

    assert "tomshardware" in registry
    assert registry["tomshardware"].display_name == "Tom's Hardware"
    assert TOMSHARDWARE_ROOT == "https://www.tomshardware.com"
