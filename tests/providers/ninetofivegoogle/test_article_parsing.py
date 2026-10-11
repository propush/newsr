from __future__ import annotations

from pathlib import Path

from newsr.domain import SectionCandidate
from newsr.providers.ninetofivegoogle.parsing import parse_article_html


def test_parse_article_html_extracts_title() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_article_pixel_features.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/04/03/google-pixel-10-pro-features",
        provider_id="ninetofivegoogle",
        provider_article_id="2026/04/03/google-pixel-10-pro-features",
        url="https://9to5google.com/2026/04/03/google-pixel-10-pro-features/",
        category="Pixel",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Google Pixel 10 Pro gets a surprising new feature"


def test_parse_article_html_extracts_author() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_article_pixel_features.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/04/03/google-pixel-10-pro-features",
        provider_id="ninetofivegoogle",
        provider_article_id="2026/04/03/google-pixel-10-pro-features",
        url="https://9to5google.com/2026/04/03/google-pixel-10-pro-features/",
        category="Pixel",
    )

    article = parse_article_html(html, candidate)

    assert article.author == "Jesse Hollander"


def test_parse_article_html_extracts_published_at() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_article_pixel_features.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/04/03/google-pixel-10-pro-features",
        provider_id="ninetofivegoogle",
        provider_article_id="2026/04/03/google-pixel-10-pro-features",
        url="https://9to5google.com/2026/04/03/google-pixel-10-pro-features/",
        category="Pixel",
    )

    article = parse_article_html(html, candidate)

    assert article.published_at is not None
    assert article.published_at.year == 2026
    assert article.published_at.month == 4
    assert article.published_at.day == 3


def test_parse_article_html_extracts_body_content() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_article_pixel_features.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/04/03/google-pixel-10-pro-features",
        provider_id="ninetofivegoogle",
        provider_article_id="2026/04/03/google-pixel-10-pro-features",
        url="https://9to5google.com/2026/04/03/google-pixel-10-pro-features/",
        category="Pixel",
    )

    article = parse_article_html(html, candidate)

    assert "latest Pixel 10 Pro software update" in article.body
    assert "native support for multiple home screen layouts" in article.body
    assert "This is exactly what we needed" in article.body


def test_parse_article_html_filters_ad_content() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_article_pixel_features.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/04/03/google-pixel-10-pro-features",
        provider_id="ninetofivegoogle",
        provider_article_id="2026/04/03/google-pixel-10-pro-features",
        url="https://9to5google.com/2026/04/03/google-pixel-10-pro-features/",
        category="Pixel",
    )

    article = parse_article_html(html, candidate)

    assert "FTC: We use income earning auto affiliate links." not in article.body
    assert "You're reading 9to5Google" not in article.body
    assert "Worth checking out on Amazon" not in article.body


def test_parse_article_html_excludes_iframe_content() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_article_pixel_features.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/04/03/google-pixel-10-pro-features",
        provider_id="ninetofivegoogle",
        provider_article_id="2026/04/03/google-pixel-10-pro-features",
        url="https://9to5google.com/2026/04/03/google-pixel-10-pro-features/",
        category="Pixel",
    )

    article = parse_article_html(html, candidate)

    assert "Check out 9to5Google on YouTube" not in article.body


def test_parse_article_html_returns_canonical_url() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_article_pixel_features.html").read_text(
        encoding="utf-8"
    )
    candidate = SectionCandidate(
        article_id="2026/04/03/google-pixel-10-pro-features",
        provider_id="ninetofivegoogle",
        provider_article_id="2026/04/03/google-pixel-10-pro-features",
        url="https://9to5google.com/2026/04/03/google-pixel-10-pro-features/",
        category="Pixel",
    )

    article = parse_article_html(html, candidate)

    assert article.url == "https://9to5google.com/2026/04/03/google-pixel-10-pro-features/"


def test_parse_article_html_cleans_site_suffix_from_meta_title() -> None:
    html = """
    <html>
    <head>
        <meta property="og:title" content="Test Article - 9to5Google">
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
        provider_id="ninetofivegoogle",
        provider_article_id="2024/01/01/test-article",
        url="https://9to5google.com/2024/01/01/test-article/",
        category="Test",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "Test Article"


def test_parse_article_html_handles_missing_title() -> None:
    html = """
    <html>
    <body>
        <div id="content">
            <p>No title here, just content.</p>
            <div class="container med post-content">
                <p>Article body content.</p>
            </div>
        </div>
    </body>
    </html>
    """
    candidate = SectionCandidate(
        article_id="2024/01/01/test-article",
        provider_id="ninetofivegoogle",
        provider_article_id="2024/01/01/test-article",
        url="https://9to5google.com/2024/01/01/test-article/",
        category="Test",
    )

    article = parse_article_html(html, candidate)

    assert article.title == "2024/01/01/test-article"


def test_parse_article_html_handles_missing_author() -> None:
    html = """
    <html>
    <head>
        <meta property="og:title" content="Test Article">
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
        provider_id="ninetofivegoogle",
        provider_article_id="2024/01/01/test-article",
        url="https://9to5google.com/2024/01/01/test-article/",
        category="Test",
    )

    article = parse_article_html(html, candidate)

    assert article.author is None


def test_parse_article_html_handles_missing_published_at() -> None:
    html = """
    <html>
    <head>
        <meta property="og:title" content="Test Article">
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
        provider_id="ninetofivegoogle",
        provider_article_id="2024/01/01/test-article",
        url="https://9to5google.com/2024/01/01/test-article/",
        category="Test",
    )

    article = parse_article_html(html, candidate)

    assert article.published_at is None


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
        provider_id="ninetofivegoogle",
        provider_article_id="2024/01/01/test-article",
        url="https://9to5google.com/2024/01/01/test-article/",
        category="Test",
    )

    article = parse_article_html(html, candidate)

    assert article.published_at is None


def test_parse_article_html_handles_empty_html() -> None:
    candidate = SectionCandidate(
        article_id="2024/01/01/test-article",
        provider_id="ninetofivegoogle",
        provider_article_id="2024/01/01/test-article",
        url="https://9to5google.com/2024/01/01/test-article/",
        category="Test",
    )

    article = parse_article_html("", candidate)

    assert article.title == "2024/01/01/test-article"
    assert article.author is None
    assert article.published_at is None
    assert article.body == ""
