from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from newsr.cancellation import RefreshCancellation
from newsr.domain import SectionCandidate
from newsr.providers.paymentsdive import (
    DEFAULT_TARGET_SLUGS,
    PAYMENTSDIVE_ROOT,
    PaymentsDiveProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry
from newsr.storage import NewsStorage
from newsr.ui.controllers.provider_home import ProviderHomeController


def _fixture(name: str) -> str:
    return Path("tests/fixtures", name).read_text(encoding="utf-8")


def _candidate() -> SectionCandidate:
    article_path = "news/fido-wrestles-with-agentic-trust/831380"
    return SectionCandidate(
        article_id=f"paymentsdive:{article_path}",
        provider_id="paymentsdive",
        provider_article_id=article_path,
        url=f"{PAYMENTSDIVE_ROOT}/{article_path}/",
        category="Technology",
    )


def test_catalog_has_latest_and_live_topic_paths() -> None:
    provider = PaymentsDiveProvider()
    targets = provider.default_targets()

    assert [(target.target_key, target.label, target.payload["path"]) for target in targets] == [
        ("latest", "Latest", "/"),
        ("retail", "Retail", "/topic/retail/"),
        ("banking", "Banking", "/topic/banking/"),
        ("restaurants", "Restaurants", "/topic/restaurants/"),
        ("regulations_and_policy", "Regulations & Policy", "/topic/regulations_and_policy/"),
        ("risk", "Consumer Risk", "/topic/risk/"),
        ("technology", "Technology", "/topic/technology/"),
        ("b2b", "B2B", "/topic/b2b/"),
        ("fraud", "Fraud", "/topic/fraud/"),
    ]
    assert all(target.provider_id == "paymentsdive" and target.target_kind == "category" for target in targets)
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS
    assert provider.discover_targets() == targets


def test_latest_listing_includes_hero_and_top_stories_without_duplicates() -> None:
    candidates = parse_section_html(_fixture("paymentsdive_listing_latest.html"), "Latest")

    assert [candidate.provider_article_id for candidate in candidates] == [
        "news/fido-wrestles-with-agentic-trust/831380",
        "news/ach-use-rises-for-b2b-payments/831270",
        "news/amazon-meta-muse-ai-agentic-shopping-experience/831052",
    ]
    assert all(candidate.provider_id == "paymentsdive" and candidate.category == "Latest" for candidate in candidates)


def test_topic_listing_filters_promos_external_links_and_duplicate_urls() -> None:
    candidates = parse_section_html(_fixture("paymentsdive_listing_technology.html"), "Technology")

    assert [candidate.provider_article_id for candidate in candidates] == [
        "news/fido-wrestles-with-agentic-trust/831380",
        "news/ach-use-rises-for-b2b-payments/831270",
    ]
    assert candidates[0].url == "https://www.paymentsdive.com/news/fido-wrestles-with-agentic-trust/831380/"


def test_article_parser_extracts_metadata_and_readable_body() -> None:
    article = parse_article_html(_fixture("paymentsdive_article.html"), _candidate())

    assert article.article_id == _candidate().article_id
    assert article.provider_id == "paymentsdive"
    assert article.provider_article_id == _candidate().provider_article_id
    assert article.url == _candidate().url
    assert article.title == "FIDO wrestles with agentic trust"
    assert article.author == "Lynne Marek"
    assert article.published_at == datetime(2026, 9, 25, 10, 38)
    assert article.body == (
        "Payments players are working on safeguards for agentic commerce.\n\n"
        "Identity and trust\n\n"
        "FIDO Alliance members are discussing ways to verify buyers.\n\n"
        "Payment data can help establish trust in a transaction."
    )


def test_fetch_methods_preserve_identity_limit_and_cancellation() -> None:
    calls: list[tuple[str, RefreshCancellation | None]] = []

    class StubProvider(PaymentsDiveProvider):
        @staticmethod
        def _read_url(url: str, cancellation: RefreshCancellation | None = None) -> str:
            calls.append((url, cancellation))
            if url == _candidate().url:
                return _fixture("paymentsdive_article.html")
            return _fixture("paymentsdive_listing_technology.html")

    provider = StubProvider()
    cancellation = RefreshCancellation()
    target = next(target for target in provider.default_targets() if target.target_key == "technology")
    candidates = provider.fetch_candidates(target, limit=1, cancellation=cancellation)
    article = provider.fetch_article(candidates[0], cancellation=cancellation)

    assert calls == [
        ("https://www.paymentsdive.com/topic/technology/", cancellation),
        (_candidate().url, cancellation),
    ]
    assert len(candidates) == 1
    assert candidates[0] == _candidate()
    assert article.article_id == candidates[0].article_id
    assert article.body.startswith("Payments players are working on safeguards")


def test_url_helpers_reject_non_article_links() -> None:
    url = normalize_url(
        "http://www.paymentsdive.com/news/fido-wrestles-with-agentic-trust/831380?utm_source=home#top"
    )

    assert url == _candidate().url
    assert normalize_target_path("topic/technology") == "/topic/technology/"
    assert article_id_from_url(url) == _candidate().provider_article_id
    assert is_article_url(url)
    assert not is_article_url("https://www.paymentsdive.com/topic/technology/")
    assert not is_article_url("https://www.paymentsdive.com/spons/example/831381/")
    assert not is_article_url("https://example.com/news/example/831381/")


def test_registry_and_bootstrap_seed_disabled_provider_with_selected_targets(storage: NewsStorage) -> None:
    registry = build_provider_registry()
    assert registry["paymentsdive"].display_name == "Payments Dive"

    app = SimpleNamespace(builtin_providers=registry, storage=storage)
    ProviderHomeController(app).bootstrap()  # type: ignore[arg-type]

    record = storage.get_provider("paymentsdive")
    assert record is not None and record.enabled is False and record.provider_type == "http"
    assert {target.target_key for target in storage.list_selected_targets("paymentsdive")} == {
        "technology",
        "fraud",
    }
