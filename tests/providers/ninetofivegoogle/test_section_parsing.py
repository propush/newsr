from __future__ import annotations

from pathlib import Path

from newsr.providers.ninetofivegoogle.parsing import parse_section_html


def test_parse_section_html_extracts_unique_candidates() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_listing_pixel.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(html, "Pixel")

    article_ids = [candidate.article_id for candidate in candidates]
    assert len(article_ids) == 3
    assert "2026/04/03/google-pixel-10-pro-features" in article_ids
    assert "2026/04/03/pixel-watch-3-battery-life-improvements" in article_ids
    assert "2026/04/02/pixel-9a-launch-date-specs" in article_ids


def test_parse_section_html_rejects_non_article_links() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_listing_pixel.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(html, "Pixel")

    article_ids = [candidate.article_id for candidate in candidates]
    assert "2026/04/03/google-pixel-10-pro-features" in article_ids
    for candidate in candidates:
        assert candidate.provider_id == "ninetofivegoogle"
        assert candidate.category == "Pixel"


def test_parse_section_html_deduplicates_articles() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_listing_pixel.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(html, "Pixel")

    article_ids = [candidate.article_id for candidate in candidates]
    pixel_10_count = article_ids.count("2026/04/03/google-pixel-10-pro-features")
    assert pixel_10_count == 1


def test_parse_section_html_skips_external_site_links() -> None:
    html = Path("tests/fixtures/ninetofivegoogle_listing_pixel.html").read_text(
        encoding="utf-8"
    )

    candidates = parse_section_html(html, "Pixel")

    article_ids = [candidate.article_id for candidate in candidates]
    assert "some-mac-news" not in "".join(article_ids)


def test_parse_section_html_handles_empty_html() -> None:
    candidates = parse_section_html("", "Test")
    assert candidates == []


def test_parse_section_html_handles_malformed_html() -> None:
    candidates = parse_section_html("<html><invalid>", "Test")
    assert candidates == []


def test_parse_section_html_rejects_podcast_entries() -> None:
    html = Path(
        "tests/fixtures/ninetofivegoogle_listing_podcast.html"
    ).read_text(encoding="utf-8")

    candidates = parse_section_html(html, "Pixel")

    article_ids = [candidate.article_id for candidate in candidates]
    assert len(candidates) == 3
    assert "2026/04/03/google-pixel-10-pro-features" in article_ids
    assert "2026/04/03/pixel-watch-3-battery-life-improvements" in article_ids
    assert "2026/04/02/pixel-9a-launch-date-specs" in article_ids
    assert "2026/04/01/pixelated-094-google-io-preview" not in article_ids
    assert "2026/04/01/happy-hour-pixel-audio" not in article_ids
    assert "2026/04/01/9to5google-daily-april-1" not in article_ids
    assert "2026/04/01/overtime-pixel-watch-leak" not in article_ids
    assert "2026/03/30/the-sideload-028-the-short-life-and-quick-death-of-samsungs-trifold" not in article_ids


def test_parse_section_html_rejects_podcast_entries_nonzero_padded() -> None:
    html = """
    <html>
    <body>
        <main class="main-content">
            <div class="article-list">
                <article class="article-item">
                    <h2 class="article-title">
                        <a class="article-title-link" href="https://9to5google.com/2026/04/01/pixelated-100-google-io-preview/">
                            Pixelated 100: Google I/O Preview
                        </a>
                    </h2>
                </article>
                <article class="article-item">
                    <h2 class="article-title">
                        <a class="article-title-link" href="https://9to5google.com/2026/04/01/the-sideload-28-review/">
                            The Sideload 28: Tech Review
                        </a>
                    </h2>
                </article>
                <article class="article-item">
                    <h2 class="article-title">
                        <a class="article-title-link" href="https://9to5google.com/2026/04/01/pixelated-5-launch-event/">
                            Pixelated 5: Launch Event Recap
                        </a>
                    </h2>
                </article>
                <article class="article-item">
                    <h2 class="article-title">
                        <a class="article-title-link" href="https://9to5google.com/2026/04/03/google-pixel-10-pro-features/">
                            Google Pixel 10 Pro gets a surprising new feature
                        </a>
                    </h2>
                </article>
            </div>
        </main>
    </body>
    </html>
    """

    candidates = parse_section_html(html, "Pixel")

    article_ids = [candidate.article_id for candidate in candidates]
    assert len(candidates) == 1
    assert "2026/04/01/pixelated-100-google-io-preview" not in article_ids
    assert "2026/04/01/the-sideload-28-review" not in article_ids
    assert "2026/04/01/pixelated-5-launch-event" not in article_ids
    assert "2026/04/03/google-pixel-10-pro-features" in article_ids
