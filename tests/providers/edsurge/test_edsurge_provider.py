from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.edsurge import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    EDSURGE_ROOT,
    EdSurgeProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/edsurge_listing_k12.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "K-12")

    assert [candidate.article_id for candidate in candidates] == [
        "news/2026-03-27-the-ai-use-case-question-teachers-are-still-asking",
        "news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/edsurge_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
        provider_id="edsurge",
        provider_article_id="news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
        url="https://www.edsurge.com/news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
        category="K-12",
    )

    article = parse_article_html(html, candidate)

    assert (
        article.url
        == "https://www.edsurge.com/news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles"
    )
    assert article.title == "Which Education Jobs Are Growing the Fastest? Mostly Non-Classroom Roles."
    assert article.author == "Nadia Tamez-Robledo"
    assert article.published_at is not None
    assert "Federal data shows the education jobs with the most growth" in article.body
    assert "The rest of the list is filled by health therapy roles" in article.body
    assert "Sign up for our newsletter" not in article.body
    assert "More from EdSurge" not in article.body
    assert "Nadia Tamez-Robledo is a reporter covering K-12 education" not in article.body


def test_discover_targets_returns_static_catalog() -> None:
    provider = EdSurgeProvider()

    default_targets = provider.default_targets()
    discovered_targets = provider.discover_targets()

    assert [target.target_key for target in discovered_targets] == [
        target.target_key for target in default_targets
    ]


def test_default_targets_match_curated_edsurge_catalog() -> None:
    targets = EdSurgeProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "k12",
        "higher-ed",
        "artificial-intelligence",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/news/k-12"},
        {"path": "/news/higher-ed"},
        {"path": "/news/topics/artificial-intelligence"},
    ]
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/edsurge_listing_k12.html").read_text(encoding="utf-8")

    class StubProvider(EdSurgeProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    target = ProviderTarget(
        provider_id="edsurge",
        target_key="k12",
        target_kind="category",
        label="K-12",
        payload={"path": "/news/k-12"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=5)

    assert [(candidate.article_id, candidate.provider_article_id, candidate.category) for candidate in candidates] == [
        (
            "edsurge:news/2026-03-27-the-ai-use-case-question-teachers-are-still-asking",
            "news/2026-03-27-the-ai-use-case-question-teachers-are-still-asking",
            "K-12",
        ),
        (
            "edsurge:news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
            "news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
            "K-12",
        ),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/edsurge_article.html").read_text(encoding="utf-8")

    class StubProvider(EdSurgeProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="edsurge:news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
        provider_id="edsurge",
        provider_article_id="news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
        url="https://www.edsurge.com/news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles",
        category="K-12",
    )

    article = StubProvider().fetch_article(candidate)

    assert (
        article.article_id
        == "edsurge:news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles"
    )
    assert article.provider_id == "edsurge"
    assert (
        article.provider_article_id
        == "news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles"
    )
    assert article.title == "Which Education Jobs Are Growing the Fastest? Mostly Non-Classroom Roles."


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://www.edsurge.com/news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles?utm_source=test#top"
    )

    assert (
        url
        == "https://www.edsurge.com/news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles"
    )
    assert normalize_target_path("news/k-12") == "/news/k-12"
    assert is_article_url(url) is True
    assert is_article_url("https://www.edsurge.com/news/k-12") is False
    assert is_article_url("https://www.edsurge.com/news/topics/artificial-intelligence") is False
    assert is_article_url("https://www.edsurge.com/jobs/example-role") is False
    assert article_id_from_url(url) == "news/2026-03-26-which-education-jobs-are-growing-the-fastest-mostly-non-classroom-roles"


def test_registry_includes_edsurge_provider() -> None:
    registry = build_provider_registry()

    assert "edsurge" in registry
    assert registry["edsurge"].display_name == "EdSurge"
    assert EDSURGE_ROOT == "https://www.edsurge.com"
