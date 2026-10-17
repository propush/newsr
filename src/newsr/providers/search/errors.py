from __future__ import annotations

from math import ceil


class SearchUnavailableError(RuntimeError):
    """Raised when the upstream search provider returns no usable results page."""


class SearchChallengeError(SearchUnavailableError):
    """Raised when DuckDuckGo keeps answering with an anti-bot challenge page."""

    def __init__(self, message: str, *, browser_url: str) -> None:
        super().__init__(message)
        self.browser_url = browser_url


class SearchCooldownError(SearchUnavailableError):
    """Raised for background searches while DuckDuckGo search is cooling down."""

    def __init__(self, remaining_seconds: float) -> None:
        super().__init__(
            "DuckDuckGo search is paused after an anti-bot challenge;"
            f" retry in {ceil(remaining_seconds)} s."
        )
        self.remaining_seconds = remaining_seconds
