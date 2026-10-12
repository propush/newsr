from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from newsr.providers.tts.base import TTSEngineError
from newsr.providers.tts.http import post_for_bytes


class FakeAudioResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> FakeAudioResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._body)
        data, self._body = self._body[:size], self._body[size:]
        return data

    def close(self) -> None:
        return None


def http_error(code: int, body: bytes = b"") -> HTTPError:
    return HTTPError("https://tts.example/speech", code, "error", {}, io.BytesIO(body))  # type: ignore[arg-type]


def install_urlopen(monkeypatch: pytest.MonkeyPatch, plan: list[object]) -> list[object]:
    requests: list[object] = []

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        requests.append(request)
        outcome = plan.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr("newsr.providers.transport.urlopen", fake_urlopen)
    return requests


def test_post_for_bytes_sends_json_and_returns_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = install_urlopen(monkeypatch, [FakeAudioResponse(b"mp3-bytes")])

    data = post_for_bytes(
        "https://tts.example/speech",
        {"input": "Hello"},
        engine="test",
        headers={"Authorization": "Bearer key"},
        request_retries=0,
    )

    assert data == b"mp3-bytes"
    request = requests[0]
    assert json.loads(request.data) == {"input": "Hello"}
    assert request.get_header("Authorization") == "Bearer key"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_method() == "POST"


def test_post_for_bytes_retries_transient_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    install_urlopen(monkeypatch, [http_error(503), URLError("reset"), FakeAudioResponse(b"ok")])

    data = post_for_bytes("https://tts.example/speech", {"input": "Hi"}, engine="test", headers={}, request_retries=2)

    assert data == b"ok"


def test_post_for_bytes_reports_client_errors_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    plan: list[object] = [http_error(401, b'{"error": "bad key"}'), FakeAudioResponse(b"unused")]
    install_urlopen(monkeypatch, plan)

    with pytest.raises(TTSEngineError, match='HTTP 401: {"error": "bad key"}'):
        post_for_bytes("https://tts.example/speech", {"input": "Hi"}, engine="test", headers={}, request_retries=3)
    assert len(plan) == 1
