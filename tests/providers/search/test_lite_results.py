from __future__ import annotations

from pathlib import Path

from newsr.providers.search import SearchResult, parse_lite_results


def test_parse_lite_results_extracts_organic_results_and_snippets() -> None:
    html = Path("tests/fixtures/duckduckgo_lite_results.html").read_text(encoding="utf-8")

    results = parse_lite_results(html)

    assert results == [
        SearchResult(
            title="Textual",
            url="https://textual.textualize.io/",
            snippet="Textual is a TUI framework for Python , inspired by modern web development.",
        ),
        SearchResult(
            title="GitHub - Textualize/textual",
            url="https://github.com/Textualize/textual",
            snippet="The lean application framework for Python.",
        ),
        SearchResult(
            title="textual · PyPI",
            url="https://pypi.org/project/textual/",
            snippet="",
        ),
    ]


def test_parse_lite_results_skips_ad_redirect_links_outside_sponsored_rows() -> None:
    html = """
    <table>
      <tr><td><a class="result-link" href="https://duckduckgo.com/y.js?ad_domain=ads.example">Ad</a></td></tr>
      <tr><td class="result-snippet">Ad snippet.</td></tr>
      <tr><td><a class="result-link" href="https://example.com/story">Story</a></td></tr>
      <tr><td class="result-snippet">Story snippet.</td></tr>
    </table>
    """

    assert parse_lite_results(html) == [
        SearchResult(title="Story", url="https://example.com/story", snippet="Story snippet.")
    ]
