from __future__ import annotations

from typing import Any, Callable, Mapping

from newsr.cancellation import RefreshCancellation
from newsr.providers.search import DuckDuckGoSearchClient, SearchResponse, SearchThrottle

RESULTS_HTML = """
<html>
  <body>
    <div class="result">
      <h2 class="result__title">
        <a class="result__a" href="https://example.com/story">Example Story</a>
      </h2>
      <div class="result__snippet">Useful background context.</div>
    </div>
  </body>
</html>
"""

LITE_RESULTS_HTML = """
<table>
  <tr><td>1.</td><td><a class="result-link" href="https://example.com/lite">Lite Story</a></td></tr>
  <tr><td></td><td class="result-snippet">Lite snippet.</td></tr>
</table>
"""

CHALLENGE_HTML = """
<html>
  <body>
    <form id="challenge-form">
      <div class="anomaly-modal__title">Unfortunately, bots use DuckDuckGo too.</div>
    </form>
  </body>
</html>
"""

ScriptedResponse = SearchResponse | BaseException | Callable[[RefreshCancellation | None], SearchResponse]


class FakeSearchTransport:
    def __init__(self, *responses: ScriptedResponse) -> None:
        self.responses = list(responses)
        self.posts: list[dict[str, Any]] = []
        self.resets = 0

    def post(
        self,
        url: str,
        form: Mapping[str, str],
        *,
        headers: Mapping[str, str],
        cancellation: RefreshCancellation | None = None,
        timeout: float = 30,
    ) -> SearchResponse:
        self.posts.append(
            {
                "url": url,
                "form": dict(form),
                "headers": dict(headers),
                "cancellation": cancellation,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("unexpected DuckDuckGo request")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        if callable(response):
            return response(cancellation)
        return response

    def reset(self) -> None:
        self.resets += 1


def instant_throttle(**kwargs: Any) -> SearchThrottle:
    return SearchThrottle(min_interval=0, jitter=0, **kwargs)


def make_client(
    transport: FakeSearchTransport,
    *,
    request_retries: int = 2,
    throttle: SearchThrottle | None = None,
    on_challenge: Callable[[str], None] | None = None,
) -> DuckDuckGoSearchClient:
    return DuckDuckGoSearchClient(
        request_retries=request_retries,
        transport=transport,
        throttle=throttle or instant_throttle(),
        on_challenge=on_challenge,
    )
