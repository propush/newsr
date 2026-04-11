from __future__ import annotations

import pytest

from newsr.cancellation import RefreshCancellation, RefreshCancelled
from newsr.providers.transport import browser_headers, newsr_headers, read_text_response, read_text_url


class FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            data = self._body
            self._body = b""
            return data
        if not self._body:
            return b""
        data = self._body[:size]
        self._body = self._body[size:]
        return data

    def close(self) -> None:
        return None


def test_read_text_url_uses_newsr_user_agent_and_remaining_cancellation_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["user_agent"] = request.get_header("User-agent")
        captured["timeout"] = timeout
        return FakeHTTPResponse(b"fixture")

    monkeypatch.setattr("newsr.providers.transport.urlopen", fake_urlopen)
    cancellation = RefreshCancellation().child_with_timeout(5)

    try:
        body = read_text_url("https://example.com/story", cancellation)
    finally:
        cancellation.finish()

    assert body == "fixture"
    assert captured["user_agent"] == newsr_headers()["User-Agent"]
    assert 0 < float(captured["timeout"]) <= 5


def test_read_text_url_supports_browser_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_user_agent: list[str | None] = []

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured_user_agent.append(request.get_header("User-agent"))
        return FakeHTTPResponse(b"fixture")

    monkeypatch.setattr("newsr.providers.transport.urlopen", fake_urlopen)

    body = read_text_url("https://example.com/story", headers=browser_headers())

    assert body == "fixture"
    assert captured_user_agent == [browser_headers()["User-Agent"]]


def test_read_text_url_checks_cancellation_before_opening_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = False

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        nonlocal opened
        opened = True
        return FakeHTTPResponse(b"fixture")

    monkeypatch.setattr("newsr.providers.transport.urlopen", fake_urlopen)
    cancellation = RefreshCancellation()
    cancellation.cancel()

    with pytest.raises(RefreshCancelled):
        read_text_url("https://example.com/story", cancellation)

    assert opened is False


def test_read_text_response_supports_replace_decode_errors() -> None:
    response = FakeHTTPResponse(b"\xffok")

    payload = read_text_response(response, errors="replace")

    assert payload == "\ufffdok"


def test_read_text_url_supports_post_requests_with_custom_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["method"] = request.get_method()
        captured["content_type"] = request.get_header("Content-type")
        captured["target"] = request.get_header("D-target")
        captured["body"] = request.data
        return FakeHTTPResponse(b"{\"ok\": true}")

    monkeypatch.setattr("newsr.providers.transport.urlopen", fake_urlopen)

    payload = read_text_url(
        "https://example.com/search",
        data=b'{"query":"ai"}',
        headers=newsr_headers(
            {
                "Content-Type": "application/json",
                "d-target": "elastic",
            }
        ),
        method="POST",
    )

    assert payload == "{\"ok\": true}"
    assert captured == {
        "method": "POST",
        "content_type": "application/json",
        "target": "elastic",
        "body": b'{"query":"ai"}',
    }
