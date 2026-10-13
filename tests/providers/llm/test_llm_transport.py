from __future__ import annotations

import http.client
import logging
import socket

import pytest

from newsr.cancellation import RefreshCancellation, RefreshCancelled
from newsr.providers.llm import OpenAILLMClient

from tests.providers.llm.http_fakes import (
    FakeHTTPConnection,
    FakeHTTPSConnection,
    FakeResponse,
    make_config,
)


class FailingReadResponse(FakeResponse):
    def __init__(
        self,
        error: Exception,
        *,
        cancellation: RefreshCancellation | None = None,
    ) -> None:
        super().__init__({"choices": []})
        self._error = error
        self._cancellation = cancellation

    def read(self, _size: int = -1) -> bytes:
        if self._cancellation is not None:
            self._cancellation.cancel()
        raise self._error


def test_llm_client_uses_bearer_auth_and_extra_headers() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "translated"}}]}),
    ]
    client = OpenAILLMClient(
        make_config(
            api_key="sk-test",
            headers={"OpenAI-Organization": "org-test"},
        )
    )

    result = client.translate_title("Headline")

    assert result == "translated"
    assert len(FakeHTTPConnection.requests) == 1
    request = FakeHTTPConnection.requests[0]
    assert request["host"] == "localhost"
    assert request["port"] == 8081
    assert request["method"] == "POST"
    assert request["path"] == "/v1/chat/completions"
    assert isinstance(request["body"], bytes)
    assert request["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-test",
        "OpenAI-Organization": "org-test",
    }


def test_llm_client_uses_https_for_hosted_endpoints() -> None:
    FakeHTTPSConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "translated"}}]}),
    ]
    client = OpenAILLMClient(make_config(url="https://api.openai.com/v1"))

    result = client.translate_title("Headline")

    assert result == "translated"
    assert len(FakeHTTPSConnection.requests) == 1
    assert FakeHTTPSConnection.requests[0]["host"] == "api.openai.com"
    assert FakeHTTPSConnection.requests[0]["port"] == 443
    assert FakeHTTPSConnection.requests[0]["path"] == "/v1/chat/completions"
    assert FakeHTTPConnection.requests == []


def test_llm_client_retries_transient_transport_failures() -> None:
    FakeHTTPConnection.plan = [
        http.client.RemoteDisconnected("temporary disconnect"),
        FakeResponse({"choices": [{"message": {"content": "translated"}}]}),
    ]
    client = OpenAILLMClient(make_config(request_retries=1))

    result = client.translate_title("Headline")

    assert result == "translated"
    assert len(FakeHTTPConnection.requests) == 2
    assert len(FakeHTTPConnection.instances) == 2
    assert FakeHTTPConnection.instances[0].closed is True


def test_llm_client_reopens_connection_the_server_closed_while_idle(caplog) -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "first"}}]}),
        FakeResponse({"choices": [{"message": {"content": "second"}}]}),
    ]
    client = OpenAILLMClient(make_config(request_retries=1))
    assert client.translate_title("One") == "first"
    server_end, client_end = socket.socketpair()
    FakeHTTPConnection.instances[0].sock = client_end
    server_end.close()
    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="newsr.llm"):
            result = client.translate_title("Two")
    finally:
        logger.propagate = original_propagate
        client_end.close()

    assert result == "second"
    assert len(FakeHTTPConnection.requests) == 2
    assert len(FakeHTTPConnection.instances) == 2
    assert FakeHTTPConnection.instances[0].closed is True
    assert not any("request_retry" in record.message for record in caplog.records)


def test_llm_client_reuses_idle_connection_the_server_keeps_open() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "first"}}]}),
        FakeResponse({"choices": [{"message": {"content": "second"}}]}),
    ]
    client = OpenAILLMClient(make_config())
    assert client.translate_title("One") == "first"
    server_end, client_end = socket.socketpair()
    FakeHTTPConnection.instances[0].sock = client_end
    try:
        result = client.translate_title("Two")
    finally:
        server_end.close()
        client_end.close()

    assert result == "second"
    assert len(FakeHTTPConnection.instances) == 1
    assert FakeHTTPConnection.instances[0].closed is False


def test_llm_client_retries_transient_response_read_failures() -> None:
    FakeHTTPConnection.plan = [
        FailingReadResponse(http.client.IncompleteRead(b"partial")),
        FakeResponse({"choices": [{"message": {"content": "translated"}}]}),
    ]
    client = OpenAILLMClient(make_config(request_retries=1))

    result = client.translate_title("Headline")

    assert result == "translated"
    assert len(FakeHTTPConnection.requests) == 2
    assert len(FakeHTTPConnection.instances) == 2
    assert FakeHTTPConnection.instances[0].closed is True


def test_llm_client_raises_after_response_read_retry_budget_is_exhausted() -> None:
    FakeHTTPConnection.plan = [
        FailingReadResponse(http.client.IncompleteRead(b"partial one")),
        FailingReadResponse(http.client.IncompleteRead(b"partial two")),
    ]
    client = OpenAILLMClient(make_config(request_retries=1))

    with pytest.raises(http.client.IncompleteRead):
        client.translate_title("Headline")

    assert len(FakeHTTPConnection.requests) == 2


def test_llm_client_cancellation_prevents_response_read_retry() -> None:
    cancellation = RefreshCancellation()
    FakeHTTPConnection.plan = [
        FailingReadResponse(
            http.client.IncompleteRead(b"partial"),
            cancellation=cancellation,
        ),
    ]
    client = OpenAILLMClient(make_config(request_retries=2))

    with pytest.raises(RefreshCancelled):
        client.translate_title("Headline", cancellation)

    assert len(FakeHTTPConnection.requests) == 1


def test_llm_client_raises_http_errors_without_retrying() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"error": {"message": "bad api key"}}, status=401),
    ]
    client = OpenAILLMClient(make_config(api_key="sk-test", request_retries=2))

    with pytest.raises(RuntimeError, match="HTTP 401: bad api key"):
        client.translate_title("Headline")

    assert len(FakeHTTPConnection.requests) == 1


def test_llm_client_uses_remaining_cancellation_budget_for_connection_timeout() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "translated"}}]}),
    ]
    client = OpenAILLMClient(make_config())
    cancellation = RefreshCancellation().child_with_timeout(5)

    try:
        result = client.translate_title("Headline", cancellation)
    finally:
        cancellation.finish()

    assert result == "translated"
    assert len(FakeHTTPConnection.instances) == 1
    assert 0 < FakeHTTPConnection.instances[0].timeout <= 5


def test_llm_client_logs_request_lifecycle(caplog) -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "translated"}}]}),
    ]
    client = OpenAILLMClient(make_config())
    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="newsr.llm"):
            result = client.translate_title("Headline")
    finally:
        logger.propagate = original_propagate

    assert result == "translated"
    assert any("request_start" in record.message for record in caplog.records)
    assert any("request_done" in record.message for record in caplog.records)
