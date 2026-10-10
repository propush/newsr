from __future__ import annotations

from pathlib import Path

import pytest

from newsr.domain import SectionCandidate
from newsr.providers.bbc import parsing as bbc
from newsr.providers.edsurge import parsing as edsurge
from newsr.providers.edsurge.urls import is_article_url as is_edsurge_article
from newsr.providers.hbr import parsing as hbr
from newsr.providers.hyperallergic import parsing as hyperallergic
from newsr.providers.ninetofivegoogle import parsing as google
from newsr.providers.tomshardware import parsing as tomshardware


def test_bbc_navigation_discovers_regions_and_top_level_sections() -> None:
    html = Path("tests/fixtures/bbc_navigation_current.html").read_text()
    categories = bbc.parse_category_catalog_html(html)

    assert [(category.slug, category.path) for category in categories] == [
        ("latest", "/news"), ("technology", "/technology"), ("business", "/business"),
        ("world/africa", None), ("science-environment", "/news/science_and_environment"),
        ("bbcverify", None), ("arts", "/arts"),
    ]
    candidates = bbc.parse_section_html(html, "Arts")
    assert [candidate.article_id for candidate in candidates] == [
        "example123", "20261001-example-feature", "20261002-another-feature",
    ]


def test_edsurge_homepage_extracts_written_articles_and_filters_podcasts() -> None:
    html = Path("tests/fixtures/edsurge_listing_current.html").read_text()
    candidates = edsurge.parse_section_html(html, "Latest")

    assert [candidate.provider_article_id for candidate in candidates] == [
        "news/example-education-report", "news/example-second-report",
    ]


def test_edsurge_urls_accept_current_and_dated_articles_and_reject_category_indexes() -> None:
    assert is_edsurge_article("https://www.edsurge.com/news/example-current-report")
    assert is_edsurge_article("https://www.edsurge.com/news/2026-03-27-what%27s-next")
    assert not is_edsurge_article("https://www.edsurge.com/news/k-12")
    assert not is_edsurge_article("https://www.edsurge.com/coverage-areas/artificial-intelligence")
    assert not is_edsurge_article("https://example.com/news/example-current-report")


def test_edsurge_article_extracts_body_author_and_date() -> None:
    html = Path("tests/fixtures/edsurge_article_current.html").read_text()
    candidate = SectionCandidate(
        article_id="news/example-education-report", provider_id="edsurge",
        provider_article_id="news/example-education-report",
        url="https://www.edsurge.com/news/example-education-report", category="Latest",
    )
    article = edsurge.parse_article_html(html, candidate)

    assert article.title == "Example education report"
    assert article.author == "Example Reporter"
    assert article.published_at.isoformat() == "2026-10-07T00:00:00"
    assert article.body == (
        "The classroom research report starts here.\n\nResearch findings\n\n"
        "The second paragraph explains the results."
    )


def test_hbr_topic_results_extract_only_digital_articles() -> None:
    html = Path("tests/fixtures/hbr_listing_current.html").read_text()
    candidates = hbr.parse_section_html(html, "Leadership")

    assert [candidate.provider_article_id for candidate in candidates] == [
        "2026/10/example-leadership-report",
    ]


@pytest.mark.parametrize("payload", ["invalid", "null", "[]", '{"props": []}', '{"props":{"pageProps":{"staticState":null}}}'])
def test_malformed_hbr_topic_state_does_not_hide_legacy_cards(payload) -> None:
    html = Path("tests/fixtures/hbr_listing_leadership.html").read_text()
    expected = hbr.parse_section_html(html, "Leadership")
    html += f'<script id="__NEXT_DATA__" type="application/json">{payload}</script>'

    assert hbr.parse_section_html(html, "Leadership") == expected


def test_youtube_taxonomy_does_not_hide_written_article_cards() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_listing_youtube.html").read_text()
    candidates = google.parse_section_html(html, "YouTube")

    assert [candidate.provider_article_id for candidate in candidates] == [
        "2026/10/01/example-youtube-news",
    ]


def test_tomshardware_news_index_accepts_networking_and_legacy_urls() -> None:
    html = Path("tests/fixtures/tomshardware_listing_networking.html").read_text()
    candidates = tomshardware.parse_section_html(html, "Networking")

    assert [candidate.provider_article_id for candidate in candidates] == [
        "networking/example-networking-report", "news/example-legacy-report,12345.html",
    ]


def test_hyperallergic_explicit_opportunities_category_accepts_editorial_cards() -> None:
    html = """
    <div class="gh-feed">
      <article class="gh-card"><span class="gh-card-tag">Opportunities</span>
        <a class="gh-card-link" href="/opportunities-in-october/">Opportunities in October</a>
      </article>
      <article class="gh-card sponsored"><span class="gh-card-tag">Sponsored</span>
        <a class="gh-card-link" href="/sponsored-opportunity/">Sponsored opportunity</a>
      </article>
    </div>
    """

    assert hyperallergic.parse_section_html(html, "News") == []
    assert [candidate.provider_article_id for candidate in hyperallergic.parse_section_html(html, "Opportunities")] == [
        "opportunities-in-october",
    ]
