from __future__ import annotations

import http.client
import json

import pytest

from newsr.config import (
    AppConfig,
    ArticlesConfig,
    ExportConfig,
    ExportImageConfig,
    LLMConfig,
    ProviderSortConfig,
    TranslationConfig,
    UIConfig,
)
from newsr.providers.llm import OpenAILLMClient


class FakeResponse:
    def __init__(self, payload: dict[str, object], *, status: int = 200) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self, _size: int = -1) -> bytes:
        if _size < 0:
            data = self._body
            self._body = b""
            return data
        if not self._body:
            return b""
        data = self._body[:_size]
        self._body = self._body[_size:]
        return data

    def close(self) -> None:
        return None


class FakeHTTPConnection:
    plan: list[object] = []
    requests: list[dict[str, object]] = []
    instances: list["FakeHTTPConnection"] = []

    def __init__(self, host: str, port: int, timeout: int = 300) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.closed = False
        self.__class__.instances.append(self)

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.__class__.requests.append(
            {
                "host": self.host,
                "port": self.port,
                "method": method,
                "path": path,
                "body": body,
                "headers": dict(headers or {}),
            }
        )
        if not self.__class__.plan:
            raise AssertionError("No fake response plan configured")
        current = self.__class__.plan[0]
        if isinstance(current, Exception):
            self.__class__.plan.pop(0)
            raise current

    def getresponse(self) -> FakeResponse:
        if not self.__class__.plan:
            raise AssertionError("No fake response plan configured")
        current = self.__class__.plan.pop(0)
        if isinstance(current, Exception):
            raise AssertionError("Exceptions should be raised during request()")
        return current

    def close(self) -> None:
        self.closed = True


class FakeHTTPSConnection(FakeHTTPConnection):
    pass


@pytest.fixture(autouse=True)
def reset_fake_connections(monkeypatch) -> None:
    FakeHTTPConnection.plan = []
    FakeHTTPConnection.requests = []
    FakeHTTPConnection.instances = []
    FakeHTTPSConnection.plan = []
    FakeHTTPSConnection.requests = []
    FakeHTTPSConnection.instances = []
    monkeypatch.setattr(http.client, "HTTPConnection", FakeHTTPConnection)
    monkeypatch.setattr(http.client, "HTTPSConnection", FakeHTTPSConnection)


def make_config(
    *,
    url: str = "http://localhost:8081/v1",
    api_key: str | None = None,
    headers: dict[str, str] | None = None,
    request_retries: int = 2,
) -> AppConfig:
    return AppConfig(
        articles=ArticlesConfig(fetch=2, store=10),
        llm=LLMConfig(
            url=url,
            model_translation="translate",
            model_summary="summary",
            api_key=api_key,
            headers=headers or {},
            request_retries=request_retries,
        ),
        translation=TranslationConfig(target_language="Russian"),
        ui=UIConfig(
            locale="en",
            show_all=True,
            provider_sort=ProviderSortConfig(primary="unread", direction="desc"),
        ),
        export=ExportConfig(image=ExportImageConfig(quality="hd")),
    )


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


def test_llm_client_raises_http_errors_without_retrying() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"error": {"message": "bad api key"}}, status=401),
    ]
    client = OpenAILLMClient(make_config(api_key="sk-test", request_retries=2))

    with pytest.raises(RuntimeError, match="HTTP 401: bad api key"):
        client.translate_title("Headline")

    assert len(FakeHTTPConnection.requests) == 1


def test_llm_client_classifies_articles_with_translation_model_and_json_array_response() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "[\"SCIENCE\", \"TECHNOLOGIES\"]"}}]}),
    ]
    client = OpenAILLMClient(make_config())

    result = client.classify_article_categories("Headline", "Article body")

    assert result == ("TECHNOLOGIES", "SCIENCE")
    request = FakeHTTPConnection.requests[0]
    payload = json.loads(request["body"].decode("utf-8"))
    assert payload["model"] == "translate"
    assert "Return a JSON array" in payload["messages"][0]["content"]
    assert "at least one label" in payload["messages"][0]["content"]
    assert "AI" in payload["messages"][0]["content"]
    assert "WAR" in payload["messages"][0]["content"]


def test_llm_client_classification_parser_accepts_plain_comma_separated_labels() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "SCIENCE, TECHNOLOGIES"}}]}),
    ]
    client = OpenAILLMClient(make_config())

    result = client.classify_article_categories("Headline", "Article body")

    assert result == ("TECHNOLOGIES", "SCIENCE")


def test_llm_client_retries_empty_classification_until_it_gets_a_label() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "[]"}}]}),
        FakeResponse({"choices": [{"message": {"content": "[\"SCIENCE\"]"}}]}),
    ]
    client = OpenAILLMClient(make_config(request_retries=1))

    result = client.classify_article_categories("Headline", "Article body")

    assert result == ("SCIENCE",)
    assert len(FakeHTTPConnection.requests) == 2


def test_llm_client_retries_malformed_classification_until_it_gets_a_label() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "{\"label\": \"SCIENCE\"}"}}]}),
        FakeResponse({"choices": [{"message": {"content": "[\"SCIENCE\"]"}}]}),
    ]
    client = OpenAILLMClient(make_config(request_retries=1))

    result = client.classify_article_categories("Headline", "Article body")

    assert result == ("SCIENCE",)
    assert len(FakeHTTPConnection.requests) == 2


def test_llm_client_returns_empty_classification_after_retry_budget_is_exhausted() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "[]"}}]}),
        FakeResponse({"choices": [{"message": {"content": "not-a-category"}}]}),
    ]
    client = OpenAILLMClient(make_config(request_retries=1))

    result = client.classify_article_categories("Headline", "Article body")

    assert result == ()
    assert len(FakeHTTPConnection.requests) == 2
