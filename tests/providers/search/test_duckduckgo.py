from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import logging
import time
from typing import Iterator

from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError
import pytest

from newsr.cancellation import RefreshCancellation, RefreshCancelled
from newsr.providers.search import (
    DUCKDUCKGO_HTML_ROOT,
    DUCKDUCKGO_LITE_ROOT,
    DuckDuckGoSearchClient,
    SearchChallengeError,
    SearchCooldownError,
    SearchResponse,
    SearchThrottle,
    SearchUnavailableError,
    parse_search_results,
)
from tests.providers.search.fakes import (
    CHALLENGE_HTML,
    LITE_RESULTS_HTML,
    RESULTS_HTML,
    FakeSearchTransport,
    instant_throttle,
    make_client,
)


@contextmanager
def captured_search_logs(caplog: pytest.LogCaptureFixture, level: int = logging.INFO) -> Iterator[None]:
    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True
    try:
        with caplog.at_level(level, logger="newsr.llm"):
            yield
    finally:
        logger.propagate = original_propagate


def log_text(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(record.message for record in caplog.records)


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



def test_parse_search_results_reads_current_html_endpoint_markup() -> None:
    html = Path("tests/fixtures/duckduckgo_html_results.html").read_text(encoding="utf-8")

    results = parse_search_results(html)

    assert [(result.title, result.url) for result in results] == [
        ("Textual", "https://textual.textualize.io/"),
        (
            "GitHub - Textualize/textual: The lean application framework for Python ...",
            "https://github.com/Textualize/textual",
        ),
        ("Python Textual: Build Beautiful UIs in the Terminal", "https://realpython.com/python-textual/"),
    ]
    assert results[0].snippet.startswith("Textual is a TUI framework for Python , inspired by")


def test_search_posts_html_form_with_browser_navigation_headers() -> None:
    transport = FakeSearchTransport(SearchResponse(status=200, text=RESULTS_HTML))

    results = make_client(transport).search("example query")

    assert [result.title for result in results] == ["Example Story"]
    assert transport.posts == [
        {
            "url": DUCKDUCKGO_HTML_ROOT,
            "form": {"q": "example query", "b": "", "kl": ""},
            "headers": {
                "Origin": "https://html.duckduckgo.com",
                "Referer": "https://html.duckduckgo.com/",
            },
            "cancellation": None,
            "timeout": 30,
        }
    ]
    assert transport.resets == 0


def test_search_logs_request_metadata_without_logging_response_body(caplog) -> None:
    transport = FakeSearchTransport(SearchResponse(status=200, text=RESULTS_HTML))

    with captured_search_logs(caplog):
        results = make_client(transport).search("example query")

    assert len(results) == 1
    assert any(
        "network_request_done" in record.message
        and "method=POST" in record.message
        and "url=https://html.duckduckgo.com/html/" in record.message
        and "endpoint=html" in record.message
        and "query=example+query" in record.message
        and "status=200" in record.message
        for record in caplog.records
    )
    text = log_text(caplog)
    assert "Example Story" not in text
    assert "Useful background context." not in text
    assert "<html>" not in text


@pytest.mark.parametrize("log_request", [True, False])
def test_search_retries_transient_transport_failures(caplog, log_request: bool) -> None:
    transport = FakeSearchTransport(
        CurlConnectionError("temporary reset"),
        SearchResponse(status=200, text=RESULTS_HTML),
    )

    with captured_search_logs(caplog, logging.WARNING):
        results = make_client(transport, request_retries=1).search(
            "example query", log_request=log_request
        )

    assert len(transport.posts) == 2
    assert [result.title for result in results] == ["Example Story"]
    retry_records = [record for record in caplog.records if "network_request_retry" in record.message]
    assert bool(retry_records) is log_request


def test_search_raises_after_transient_retry_budget_is_exhausted() -> None:
    transport = FakeSearchTransport(
        ConnectionResetError("persistent reset"),
        ConnectionResetError("persistent reset"),
    )

    with pytest.raises(ConnectionResetError, match="persistent reset"):
        make_client(transport, request_retries=1).search("example query")

    assert len(transport.posts) == 2


def test_search_cancellation_prevents_transport_retry() -> None:
    cancellation = RefreshCancellation()

    def fail_and_cancel(active_cancellation: RefreshCancellation | None) -> SearchResponse:
        assert active_cancellation is cancellation
        cancellation.cancel()
        raise ConnectionResetError("temporary reset")

    transport = FakeSearchTransport(fail_and_cancel, SearchResponse(status=200, text=RESULTS_HTML))

    with pytest.raises(RefreshCancelled):
        make_client(transport, request_retries=2).search("example query", cancellation=cancellation)

    assert len(transport.posts) == 1


def test_search_rejects_negative_retry_count() -> None:
    with pytest.raises(ValueError, match="request_retries"):
        DuckDuckGoSearchClient(request_retries=-1, transport=FakeSearchTransport())


def test_search_reports_http_error_status_without_retry_or_body_logging(caplog) -> None:
    transport = FakeSearchTransport(
        SearchResponse(status=503, text="<html>service unavailable</html>"),
        SearchResponse(status=200, text=RESULTS_HTML),
    )

    with captured_search_logs(caplog, logging.WARNING):
        with pytest.raises(SearchUnavailableError, match="HTTP 503"):
            make_client(transport).search("error query")

    assert len(transport.posts) == 1
    assert any(
        "network_request_failed" in record.message
        and "method=POST" in record.message
        and "query=error+query" in record.message
        and "status=503" in record.message
        for record in caplog.records
    )
    assert "<html>" not in log_text(caplog)


def test_search_falls_back_to_lite_endpoint_with_fresh_session_after_challenge() -> None:
    throttle = instant_throttle()
    transport = FakeSearchTransport(
        SearchResponse(status=202, text=CHALLENGE_HTML),
        SearchResponse(status=200, text=LITE_RESULTS_HTML),
    )
    challenges: list[str] = []

    results = make_client(transport, throttle=throttle, on_challenge=challenges.append).search(
        "example query"
    )

    assert [(result.title, result.url, result.snippet) for result in results] == [
        ("Lite Story", "https://example.com/lite", "Lite snippet.")
    ]
    assert transport.resets == 1
    assert [post["url"] for post in transport.posts] == [DUCKDUCKGO_HTML_ROOT, DUCKDUCKGO_LITE_ROOT]
    assert transport.posts[1]["form"] == {"q": "example query", "kl": ""}
    assert transport.posts[1]["headers"] == {
        "Origin": "https://lite.duckduckgo.com",
        "Referer": "https://lite.duckduckgo.com/",
    }
    assert challenges == []
    assert throttle.cooldown_remaining() == 0


def test_search_paces_lite_fallback_request() -> None:
    waits: list[float] = []
    throttle = SearchThrottle(
        min_interval=2.0,
        jitter=0,
        clock=lambda: 100.0,
        wait=lambda delay, cancellation: waits.append(delay),
    )
    transport = FakeSearchTransport(
        SearchResponse(status=202, text=CHALLENGE_HTML),
        SearchResponse(status=200, text=LITE_RESULTS_HTML),
    )

    make_client(transport, throttle=throttle).search("example query")

    assert waits == [2.0]


def test_search_raises_challenge_error_and_starts_cooldown_when_both_endpoints_challenge(caplog) -> None:
    throttle = instant_throttle()
    transport = FakeSearchTransport(
        SearchResponse(status=202, text=CHALLENGE_HTML),
        SearchResponse(status=202, text=CHALLENGE_HTML),
    )
    challenges: list[str] = []

    with captured_search_logs(caplog):
        with pytest.raises(SearchChallengeError, match="anti-bot challenge") as exc_info:
            make_client(transport, throttle=throttle, on_challenge=challenges.append).search(
                "example query"
            )

    browser_url = "https://duckduckgo.com/?q=example+query"
    assert exc_info.value.browser_url == browser_url
    assert challenges == [browser_url]
    assert throttle.cooldown_remaining() > 0
    assert any(
        "network_request_done" in record.message
        and "endpoint=html" in record.message
        and "status=202" in record.message
        for record in caplog.records
    )


def test_search_treats_challenge_body_with_200_as_challenge() -> None:
    transport = FakeSearchTransport(
        SearchResponse(status=200, text=CHALLENGE_HTML),
        SearchResponse(status=200, text=CHALLENGE_HTML),
    )

    with pytest.raises(SearchChallengeError, match="HTTP 200"):
        make_client(transport).search("example query")


def test_search_logs_challenge_and_cooldown_when_request_logging_is_disabled(caplog) -> None:
    transport = FakeSearchTransport(
        SearchResponse(status=202, text=CHALLENGE_HTML),
        SearchResponse(status=202, text=CHALLENGE_HTML),
    )

    with captured_search_logs(caplog):
        with pytest.raises(SearchChallengeError):
            make_client(transport).search("example query", log_request=False)

    text = log_text(caplog)
    assert "search_challenge" in text
    assert "endpoint=lite" in text
    assert "search_cooldown_started" in text
    assert "network_request_done" not in text


def test_background_search_during_cooldown_skips_network_and_challenge_callback(caplog) -> None:
    throttle = instant_throttle()
    throttle.record_challenge()
    transport = FakeSearchTransport()
    challenges: list[str] = []

    with captured_search_logs(caplog, logging.WARNING):
        with pytest.raises(SearchCooldownError, match="retry in"):
            make_client(transport, throttle=throttle, on_challenge=challenges.append).search(
                "topic query", log_request=False, background=True
            )

    assert transport.posts == []
    assert challenges == []
    assert "search_cooldown_skip" in log_text(caplog)


def test_interactive_search_during_cooldown_runs_and_success_clears_cooldown() -> None:
    throttle = instant_throttle()
    throttle.record_challenge()
    transport = FakeSearchTransport(SearchResponse(status=200, text=RESULTS_HTML))

    results = make_client(transport, throttle=throttle).search("example query")

    assert [result.title for result in results] == ["Example Story"]
    assert throttle.cooldown_remaining() == 0


def test_interactive_search_during_cooldown_skips_lite_fallback_when_challenged() -> None:
    throttle = instant_throttle()
    throttle.record_challenge()
    transport = FakeSearchTransport(SearchResponse(status=202, text=CHALLENGE_HTML))
    challenges: list[str] = []

    with pytest.raises(SearchChallengeError):
        make_client(transport, throttle=throttle, on_challenge=challenges.append).search("example query")

    assert [post["url"] for post in transport.posts] == [DUCKDUCKGO_HTML_ROOT]
    assert transport.resets == 1
    assert challenges == ["https://duckduckgo.com/?q=example+query"]


def test_logged_request_duration_excludes_pacing_wait(caplog) -> None:
    throttle = SearchThrottle(
        min_interval=30.0,
        jitter=0,
        wait=lambda delay, cancellation: time.sleep(0.3),
    )
    transport = FakeSearchTransport(
        SearchResponse(status=200, text=RESULTS_HTML),
        SearchResponse(status=200, text=RESULTS_HTML),
    )
    client = make_client(transport, throttle=throttle)

    with captured_search_logs(caplog):
        client.search("first query")
        client.search("second query")

    durations = [
        float(record.message.rsplit("duration_s=", 1)[1])
        for record in caplog.records
        if "network_request_done" in record.message
    ]
    assert len(durations) == 2
    assert all(duration < 0.3 for duration in durations)


def test_challenge_callback_failure_does_not_hide_challenge_error() -> None:
    transport = FakeSearchTransport(
        SearchResponse(status=202, text=CHALLENGE_HTML),
        SearchResponse(status=202, text=CHALLENGE_HTML),
    )

    def fail(url: str) -> None:
        raise RuntimeError("app is closing")

    with pytest.raises(SearchChallengeError):
        make_client(transport, on_challenge=fail).search("example query")
