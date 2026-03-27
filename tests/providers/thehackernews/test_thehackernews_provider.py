from __future__ import annotations

from pathlib import Path

from newsr.domain import SectionCandidate
from newsr.providers.thehackernews import (
    BASE_SECTION_OPTIONS,
    DEFAULT_TARGET_SLUGS,
    TheHackerNewsProvider,
    article_id_from_url,
    is_article_url,
    normalize_url,
    parse_article_html,
    parse_section_html,
)


def test_parse_section_html_extracts_unique_candidates_and_rejects_promos() -> None:
    html = Path("tests/fixtures/thehackernews_section.html").read_text(encoding="utf-8")

    candidates = parse_section_html(html, "Threat Intelligence")

    assert [candidate.article_id for candidate in candidates] == [
        "2026/03/critical-vpn-zero-day-exploited",
        "2026/03/browser-hardening-guide-for-enterprises",
    ]


def test_parse_article_html_extracts_body_metadata() -> None:
    html = Path("tests/fixtures/thehackernews_article.html").read_text(encoding="utf-8")
    candidate = SectionCandidate(
        article_id="2026/03/critical-vpn-zero-day-exploited",
        provider_id="thehackernews",
        provider_article_id="2026/03/critical-vpn-zero-day-exploited",
        url="https://thehackernews.com/2026/03/critical-vpn-zero-day-exploited.html",
        category="Threat Intelligence",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Critical VPN Zero-Day Exploited Against Enterprise Gateways"
    assert article.author == "Ravie Lakshmanan"
    assert article.published_at is not None
    assert "Security teams are racing to patch" in article.body
    assert "Get Latest News in Your Inbox" not in article.body


def test_parse_article_html_extracts_blogger_style_body_without_paragraph_tags() -> None:
    candidate = SectionCandidate(
        article_id="2026/03/example-bare-text-article",
        provider_id="thehackernews",
        provider_article_id="2026/03/example-bare-text-article",
        url="https://thehackernews.com/2026/03/example-bare-text-article.html",
        category="Threat Intelligence",
    )
    html = """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta property="og:title" content="Example Bare Text Article" />
        <meta name="author" content="Ravie Lakshmanan" />
        <meta property="article:published_time" content="2026-03-24T08:15:00Z" />
      </head>
      <body>
        <article class="post-shell">
          <div class="post-header">
            <h1>Example Bare Text Article</h1>
            <time datetime="2026-03-24T08:15:00Z">Mar 24, 2026</time>
          </div>
          <div class="post-body entry-content">
            Analysts uncovered a new campaign targeting exposed gateways.<br /><br />
            The operators chained two flaws to gain remote access.<br /><br />
            <h2>Why it matters</h2>
            Defenders should patch internet-facing systems immediately.
            <ul>
              <li>Audit exposed appliances.</li>
              <li>Rotate credentials after remediation.</li>
            </ul>
            <div class="share-links">Follow us on Twitter and LinkedIn</div>
            <div class="newsletter-box">Get Latest News in Your Inbox</div>
          </div>
        </article>
      </body>
    </html>
    """

    article = parse_article_html(html, candidate)

    assert article.title == "Example Bare Text Article"
    assert article.body == (
        "Analysts uncovered a new campaign targeting exposed gateways.\n\n"
        "The operators chained two flaws to gain remote access.\n\n"
        "Why it matters\n\n"
        "Defenders should patch internet-facing systems immediately.\n\n"
        "Audit exposed appliances.\n\n"
        "Rotate credentials after remediation."
    )
    assert "Get Latest News in Your Inbox" not in article.body
    assert "Follow us on Twitter and LinkedIn" not in article.body


def test_parse_article_html_does_not_treat_site_name_as_author() -> None:
    html = Path("tests/fixtures/thehackernews_article_without_author.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/03/advisory-without-byline",
        provider_id="thehackernews",
        provider_article_id="2026/03/advisory-without-byline",
        url="https://thehackernews.com/2026/03/advisory-without-byline.html",
        category="Threat Intelligence",
    )

    article = parse_article_html(html, candidate)

    assert article.author is None


def test_discover_targets_returns_static_catalog() -> None:
    provider = TheHackerNewsProvider()

    default_targets = provider.default_targets()
    discovered_targets = provider.discover_targets()

    assert [target.target_key for target in discovered_targets] == [
        target.target_key for target in default_targets
    ]


def test_default_targets_mark_expected_core_targets_selected() -> None:
    targets = TheHackerNewsProvider().default_targets()

    assert [option.slug for option in BASE_SECTION_OPTIONS] == [
        "threat-intelligence",
        "cyber-attacks",
        "vulnerabilities",
        "expert-insights",
    ]
    assert {
        target.target_key for target in targets if target.selected
    } == DEFAULT_TARGET_SLUGS


def test_url_helpers_normalize_and_derive_stable_article_ids() -> None:
    url = normalize_url(
        "https://www.thehackernews.com/2026/03/critical-vpn-zero-day-exploited.html?utm_source=rss"
    )

    assert url == "https://www.thehackernews.com/2026/03/critical-vpn-zero-day-exploited.html"
    assert is_article_url(url) is True
    assert is_article_url("https://thehackernews.com/expert-insights/") is False
    assert is_article_url("https://thehackernews.uk/free-ebook") is False
    assert article_id_from_url(url) == "2026/03/critical-vpn-zero-day-exploited"
