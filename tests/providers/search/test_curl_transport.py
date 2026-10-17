from __future__ import annotations

from typing import Any

import pytest

from newsr.cancellation import RefreshCancellation, RefreshCancelled
from newsr.providers.search import CurlBrowserTransport, SearchResponse


class FakeCurlResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class FakeCurlSession:
    def __init__(self, impersonate: str, on_post=None) -> None:
        self.impersonate = impersonate
        self.posts: list[dict[str, Any]] = []
        self.closed = False
        self._on_post = on_post

    def post(self, url: str, **kwargs: Any) -> FakeCurlResponse:
        self.posts.append({"url": url, **kwargs})
        if self._on_post is not None:
            self._on_post()
        return FakeCurlResponse(202, "<html>challenge</html>")

    def close(self) -> None:
        self.closed = True


class SessionFactory:
    def __init__(self, on_post=None) -> None:
        self.sessions: list[FakeCurlSession] = []
        self._on_post = on_post

    def __call__(self, impersonate: str) -> FakeCurlSession:
        session = FakeCurlSession(impersonate, self._on_post)
        self.sessions.append(session)
        return session


def test_post_reuses_one_impersonating_session_and_maps_the_response() -> None:
    factory = SessionFactory()
    transport = CurlBrowserTransport(session_factory=factory)

    first = transport.post(
        "https://html.duckduckgo.com/html/",
        {"q": "query"},
        headers={"Referer": "https://html.duckduckgo.com/"},
    )
    transport.post("https://html.duckduckgo.com/html/", {"q": "next"}, headers={})

    assert first == SearchResponse(status=202, text="<html>challenge</html>")
    assert [session.impersonate for session in factory.sessions] == ["chrome"]
    assert factory.sessions[0].posts[0] == {
        "url": "https://html.duckduckgo.com/html/",
        "data": {"q": "query"},
        "headers": {"Referer": "https://html.duckduckgo.com/"},
        "timeout": 30,
    }


def test_reset_closes_the_session_and_rotates_the_browser_fingerprint() -> None:
    factory = SessionFactory()
    transport = CurlBrowserTransport(session_factory=factory)

    for _ in range(4):
        transport.post("https://html.duckduckgo.com/html/", {"q": "query"}, headers={})
        transport.reset()

    assert [session.impersonate for session in factory.sessions] == ["chrome", "safari", "firefox", "chrome"]
    assert all(session.closed for session in factory.sessions)


def test_reset_without_an_open_session_only_rotates_the_fingerprint() -> None:
    transport = CurlBrowserTransport(session_factory=SessionFactory())

    transport.reset()

    assert transport.impersonate == "safari"


def test_post_uses_the_remaining_cancellation_deadline_as_timeout() -> None:
    factory = SessionFactory()
    transport = CurlBrowserTransport(session_factory=factory)
    parent = RefreshCancellation()
    cancellation = parent.child_with_timeout(5)
    try:
        transport.post("https://html.duckduckgo.com/html/", {"q": "query"}, headers={}, cancellation=cancellation)
    finally:
        cancellation.finish()

    assert 0 < factory.sessions[0].posts[0]["timeout"] <= 5


def test_post_does_not_send_after_cancellation() -> None:
    factory = SessionFactory()
    transport = CurlBrowserTransport(session_factory=factory)
    cancellation = RefreshCancellation()
    cancellation.cancel()

    with pytest.raises(RefreshCancelled):
        transport.post("https://html.duckduckgo.com/html/", {"q": "query"}, headers={}, cancellation=cancellation)

    assert factory.sessions == []


def test_post_raises_when_cancelled_while_the_request_was_in_flight() -> None:
    cancellation = RefreshCancellation()
    transport = CurlBrowserTransport(session_factory=SessionFactory(on_post=cancellation.cancel))

    with pytest.raises(RefreshCancelled):
        transport.post("https://html.duckduckgo.com/html/", {"q": "query"}, headers={}, cancellation=cancellation)


def test_transport_requires_an_impersonation_target() -> None:
    with pytest.raises(ValueError):
        CurlBrowserTransport(())
