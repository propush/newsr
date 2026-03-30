from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.lawfare import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    LAWFARE_ROOT,
    LawfareProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_multimedia_titles() -> None:
    html = Path("tests/fixtures/lawfare_listing_surveillance_privacy.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(html, "Surveillance & Privacy")

    assert [candidate.article_id for candidate in candidates] == [
        "kodak-to-deepfakes-publicity-rights-and-abuse-of-our-likenesses",
        "fbi-says-why-get-a-warrant-when-you-have-kash",
        "fourth-amendment-law-by-analogy",
    ]
    assert "lawfare-daily-national-security-counterintelligence-and-counterespionage-a-guide-for-the-perplexed" not in {
        candidate.article_id for candidate in candidates
    }
    assert "scaling-laws-rapid-response-pod--trump-s-new-ai-framework-with-helen-toner---dean-ball" not in {
        candidate.article_id for candidate in candidates
    }


def test_parse_article_html_extracts_body_metadata_and_strips_boilerplate() -> None:
    html = Path("tests/fixtures/lawfare_article_spyware.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="spyware-based-searches-for-domestic-criminal-law-enforcement",
        provider_id="lawfare",
        provider_article_id="spyware-based-searches-for-domestic-criminal-law-enforcement",
        url="https://www.lawfaremedia.org/article/spyware-based-searches-for-domestic-criminal-law-enforcement",
        category="Surveillance & Privacy",
    )

    article = parse_article_html(html, candidate)

    assert (
        article.url
        == "https://www.lawfaremedia.org/article/spyware-based-searches-for-domestic-criminal-law-enforcement"
    )
    assert article.title == "Spyware-Based Searches for Domestic Criminal Law Enforcement"
    assert article.author == "Yotam Berger"
    assert article.published_at is not None
    assert "NSO Group's spyware business has been under intense scrutiny" in article.body
    assert "Spyware for Criminal Law Enforcement" in article.body
    assert "Spyware and the Fourth Amendment" in article.body
    assert "Subscribe to Lawfare" not in article.body
    assert "Back to Top" not in article.body


def test_discover_targets_returns_static_catalog() -> None:
    provider = LawfareProvider()

    default_targets = provider.default_targets()
    discovered_targets = provider.discover_targets()

    assert [target.target_key for target in discovered_targets] == [
        target.target_key for target in default_targets
    ]


def test_default_targets_match_curated_lawfare_catalog() -> None:
    targets = LawfareProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "cybersecurity-tech",
        "surveillance-privacy",
        "intelligence",
        "foreign-relations-international-law",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/topics/cybersecurity-tech"},
        {"path": "/topics/surveillance-privacy"},
        {"path": "/topics/intelligence"},
        {"path": "/topics/foreign-relations-international-law"},
    ]
    assert [target.target_kind for target in targets] == ["topic"] * 4
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/lawfare_listing_surveillance_privacy.html").read_text(
        encoding="utf-8"
    )

    class StubProvider(LawfareProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    target = ProviderTarget(
        provider_id="lawfare",
        target_key="surveillance-privacy",
        target_kind="topic",
        label="Surveillance & Privacy",
        payload={"path": "/topics/surveillance-privacy"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=2)

    assert [
        (candidate.article_id, candidate.provider_article_id, candidate.category)
        for candidate in candidates
    ] == [
        (
            "lawfare:kodak-to-deepfakes-publicity-rights-and-abuse-of-our-likenesses",
            "kodak-to-deepfakes-publicity-rights-and-abuse-of-our-likenesses",
            "Surveillance & Privacy",
        ),
        (
            "lawfare:fbi-says-why-get-a-warrant-when-you-have-kash",
            "fbi-says-why-get-a-warrant-when-you-have-kash",
            "Surveillance & Privacy",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/lawfare_article_spyware.html").read_text(encoding="utf-8")

    class StubProvider(LawfareProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="lawfare:spyware-based-searches-for-domestic-criminal-law-enforcement",
        provider_id="lawfare",
        provider_article_id="spyware-based-searches-for-domestic-criminal-law-enforcement",
        url="https://www.lawfaremedia.org/article/spyware-based-searches-for-domestic-criminal-law-enforcement",
        category="Surveillance & Privacy",
    )

    article = StubProvider().fetch_article(candidate)

    assert article.article_id == "lawfare:spyware-based-searches-for-domestic-criminal-law-enforcement"
    assert article.provider_id == "lawfare"
    assert article.provider_article_id == "spyware-based-searches-for-domestic-criminal-law-enforcement"
    assert article.title == "Spyware-Based Searches for Domestic Criminal Law Enforcement"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://lawfaremedia.org/article/spyware-based-searches-for-domestic-criminal-law-enforcement?utm_source=test#top"
    )

    assert (
        url
        == "https://www.lawfaremedia.org/article/spyware-based-searches-for-domestic-criminal-law-enforcement"
    )
    assert normalize_target_path("topics/intelligence/") == "/topics/intelligence"
    assert is_article_url(url) is True
    assert is_article_url("https://www.lawfaremedia.org/topics/surveillance-privacy") is False
    assert is_article_url("https://www.lawfaremedia.org/podcasts-multimedia/podcast") is False
    assert is_article_url("https://example.com/article/spyware-based-searches-for-domestic-criminal-law-enforcement") is False
    assert article_id_from_url(url) == "spyware-based-searches-for-domestic-criminal-law-enforcement"


def test_registry_includes_lawfare_provider() -> None:
    registry = build_provider_registry()

    assert "lawfare" in registry
    assert registry["lawfare"].display_name == "Lawfare"
    assert LAWFARE_ROOT == "https://www.lawfaremedia.org"
