from __future__ import annotations

from newsr.providers.search import parse_search_results


def test_parse_search_results_extracts_title_url_and_snippet() -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="https://example.com/story">Example Story</a>
          </h2>
          <a class="result__snippet">Useful background context.</a>
        </div>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="https://example.com/second">Second Story</a>
          </h2>
          <div class="result__snippet">Another snippet.</div>
        </div>
      </body>
    </html>
    """

    results = parse_search_results(html)

    assert results == [
        (
            results[0].__class__(
                title="Example Story",
                url="https://example.com/story",
                snippet="Useful background context.",
            )
        ),
        (
            results[1].__class__(
                title="Second Story",
                url="https://example.com/second",
                snippet="Another snippet.",
            )
        ),
    ]


def test_parse_search_results_unwraps_duckduckgo_redirect_links() -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.bafta.org%2Fawards%2Fgames">BAFTA Games Awards</a>
          </h2>
          <div class="result__snippet">Awards page.</div>
        </div>
      </body>
    </html>
    """

    results = parse_search_results(html)

    assert results == [
        results[0].__class__(
            title="BAFTA Games Awards",
            url="https://www.bafta.org/awards/games",
            snippet="Awards page.",
        )
    ]


def test_parse_search_results_normalizes_protocol_relative_links() -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="//example.com/story">Example Story</a>
          </h2>
          <div class="result__snippet">Useful background context.</div>
        </div>
      </body>
    </html>
    """

    results = parse_search_results(html)

    assert results == [
        results[0].__class__(
            title="Example Story",
            url="https://example.com/story",
            snippet="Useful background context.",
        )
    ]


def test_parse_search_results_escapes_non_latin_characters_in_target_url() -> None:
    html = """
    <html>
      <body>
        <div class="result">
          <h2 class="result__title">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2F%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8%2F%D0%B8%D0%B3%D1%80%D1%8B%3F%D1%82%D0%B5%D0%BC%D0%B0%3D%D0%91%D0%90%D0%A4%D0%A2%D0%90">BAFTA Games Awards</a>
          </h2>
          <div class="result__snippet">Awards page.</div>
        </div>
      </body>
    </html>
    """

    results = parse_search_results(html)

    assert results == [
        results[0].__class__(
            title="BAFTA Games Awards",
            url="https://example.com/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8/%D0%B8%D0%B3%D1%80%D1%8B?%D1%82%D0%B5%D0%BC%D0%B0=%D0%91%D0%90%D0%A4%D0%A2%D0%90",
            snippet="Awards page.",
        )
    ]
