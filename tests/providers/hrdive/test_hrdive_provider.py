from __future__ import annotations

from pathlib import Path

from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.hrdive import (
    BASE_TARGET_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    HRDIVE_ROOT,
    HRDiveProvider,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
    parse_article_html,
    parse_section_html,
)
from newsr.providers.registry import build_provider_registry


def test_parse_section_html_extracts_unique_candidates_and_rejects_non_articles() -> None:
    html = Path("tests/fixtures/hrdive_listing_talent.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "Talent")

    assert [candidate.article_id for candidate in candidates] == [
        "news/snelling-labor-market-endures/815901",
        "news/ai-skills-mandatory-survey/815904",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/hrdive_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="news/ai-skills-mandatory-survey/815904",
        provider_id="hrdive",
        provider_article_id="news/ai-skills-mandatory-survey/815904",
        url="https://www.hrdive.com/news/ai-skills-mandatory-survey/815904/",
        category="Talent",
    )

    article = parse_article_html(html, candidate)

    assert article.url == "https://www.hrdive.com/news/ai-skills-mandatory-survey/815904/"
    assert article.title == "CEOs think AI use is mandatory - but employees don't agree, survey says"
    assert article.author == "Kathryn Moody"
    assert article.published_at is not None
    assert "Several disconnects exist between C-suite executives" in article.body
    assert "Why it matters" in article.body
    assert "Employees want role-specific guidance." in article.body
    assert "Sign up for the free newsletter." not in article.body
    assert "Read more: Related coverage" not in article.body
    assert "Share this article" not in article.body
    assert "Kathryn Moody covers workplace trends for HR Dive." not in article.body


def test_parse_article_html_extracts_author_from_byline_without_capturing_toolbar_text() -> None:
    candidate = SectionCandidate(
        article_id="news/example-article/815999",
        provider_id="hrdive",
        provider_article_id="news/example-article/815999",
        url="https://www.hrdive.com/news/example-article/815999/",
        category="Talent",
    )
    html = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <title>Example Article | HR Dive</title>
      </head>
      <body>
        <main>
          <article>
            <h1>Example Article</h1>
            <div class="byline">
              <span>Published March 27, 2026</span>
              <a href="/author/lara-ewen/">Lara Ewen</a>
              <span>Contributor</span>
              <button>Share</button>
              <button>Copy link</button>
              <a href="/linkedin">LinkedIn</a>
              <a href="/x">X/Twitter</a>
              <a href="/facebook">Facebook</a>
              <button>Print</button>
              <button>License</button>
              <span>Add us on Google</span>
            </div>
            <div class="article-body">
              <p>Body paragraph.</p>
            </div>
          </article>
        </main>
      </body>
    </html>
    """

    article = parse_article_html(html, candidate)

    assert article.author == "Lara Ewen"


def test_default_targets_match_curated_hr_dive_catalog() -> None:
    targets = HRDiveProvider().default_targets()

    assert [option.slug for option in BASE_TARGET_OPTIONS] == [
        "talent",
        "compensation-benefits",
        "diversity-inclusion",
        "learning",
        "hr-management",
    ]
    assert [target.payload for target in targets] == [
        {"path": "/topic/talent/"},
        {"path": "/topic/compensation-benefits/"},
        {"path": "/topic/diversity-inclusion/"},
        {"path": "/topic/learning/"},
        {"path": "/topic/hr-management/"},
    ]
    assert {target.target_key for target in targets if target.selected} == DEFAULT_TARGET_SLUGS


def test_fetch_candidates_returns_provider_scoped_candidates_for_selected_target() -> None:
    html = Path("tests/fixtures/hrdive_listing_talent.html").read_text(encoding="utf-8")

    class StubProvider(HRDiveProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    target = ProviderTarget(
        provider_id="hrdive",
        target_key="talent",
        target_kind="category",
        label="Talent",
        payload={"path": "/topic/talent/"},
        selected=True,
    )

    candidates = StubProvider().fetch_candidates(target, limit=5)

    assert [(candidate.article_id, candidate.provider_article_id, candidate.category) for candidate in candidates] == [
        ("hrdive:news/snelling-labor-market-endures/815901", "news/snelling-labor-market-endures/815901", "Talent"),
        ("hrdive:news/ai-skills-mandatory-survey/815904", "news/ai-skills-mandatory-survey/815904", "Talent"),
    ]


def test_fetch_article_returns_provider_scoped_content() -> None:
    html = Path("tests/fixtures/hrdive_article.html").read_text(encoding="utf-8")

    class StubProvider(HRDiveProvider):
        @staticmethod
        def _read_url(url: str, cancellation=None) -> str:  # type: ignore[no-untyped-def]
            return html

    candidate = SectionCandidate(
        article_id="hrdive:news/ai-skills-mandatory-survey/815904",
        provider_id="hrdive",
        provider_article_id="news/ai-skills-mandatory-survey/815904",
        url="https://www.hrdive.com/news/ai-skills-mandatory-survey/815904/",
        category="Talent",
    )

    article = StubProvider().fetch_article(candidate)

    assert article.article_id == "hrdive:news/ai-skills-mandatory-survey/815904"
    assert article.provider_id == "hrdive"
    assert article.provider_article_id == "news/ai-skills-mandatory-survey/815904"
    assert article.title == "CEOs think AI use is mandatory - but employees don't agree, survey says"


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "http://www.hrdive.com/news/ai-skills-mandatory-survey/815904?utm_source=rss#comments"
    )

    assert url == "https://www.hrdive.com/news/ai-skills-mandatory-survey/815904/"
    assert normalize_target_path("topic/talent") == "/topic/talent/"
    assert is_article_url(url) is True
    assert is_article_url("https://www.hrdive.com/topic/talent/") is False
    assert is_article_url("https://www.hrdive.com/events/hr-leadership-summit/") is False
    assert is_article_url("https://resources.industrydive.com/webinar/example") is False
    assert article_id_from_url(url) == "news/ai-skills-mandatory-survey/815904"


def test_registry_includes_hrdive_provider() -> None:
    registry = build_provider_registry()

    assert "hrdive" in registry
    assert registry["hrdive"].display_name == "HR Dive"
    assert HRDIVE_ROOT == "https://www.hrdive.com"
