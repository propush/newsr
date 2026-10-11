from __future__ import annotations

import json

from newsr.providers.llm import OpenAILLMClient

from tests.providers.llm.http_fakes import FakeHTTPConnection, FakeResponse, make_config


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
