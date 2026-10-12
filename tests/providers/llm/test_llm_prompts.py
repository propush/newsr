from __future__ import annotations

import json

import pytest

from newsr.providers.llm import OpenAILLMClient
from newsr.providers.search.duckduckgo import SearchResult

from tests.providers.llm.http_fakes import FakeHTTPConnection, FakeResponse, make_config


def test_llm_client_check_responsive_uses_translation_model() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "OK"}}]}),
    ]
    client = OpenAILLMClient(make_config())

    client.check_responsive()

    request = FakeHTTPConnection.requests[0]
    payload = json.loads(request["body"].decode("utf-8"))
    assert payload["model"] == "translate"
    assert payload["messages"][0]["content"] == "Reply with OK only."
    assert payload["messages"][1]["content"] == "ping"


def test_llm_client_check_responsive_rejects_empty_response() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "   "}}]}),
    ]
    client = OpenAILLMClient(make_config())

    with pytest.raises(RuntimeError, match="LLM returned an empty response"):
        client.check_responsive()


def test_llm_client_brief_requests_use_summary_model_and_max_tokens() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "brief notes"}}]}),
        FakeResponse({"choices": [{"message": {"content": "brief report"}}]}),
    ]
    client = OpenAILLMClient(make_config())

    notes = client.shorten_brief_notes("Shorten in Russian.", "Long summaries", max_tokens=123)
    report = client.synthesize_brief_report("Report in Russian.", "Brief notes", max_tokens=456)

    assert notes == "brief notes"
    assert report == "brief report"
    first_payload = json.loads(FakeHTTPConnection.requests[0]["body"].decode("utf-8"))
    second_payload = json.loads(FakeHTTPConnection.requests[1]["body"].decode("utf-8"))
    assert first_payload["model"] == "summary"
    assert first_payload["max_tokens"] == 123
    assert first_payload["messages"][0]["content"] == "Shorten in Russian."
    assert second_payload["model"] == "summary"
    assert second_payload["max_tokens"] == 456
    assert second_payload["messages"][0]["content"] == "Report in Russian."


def test_llm_client_summary_prompt_includes_current_datetime(monkeypatch) -> None:
    monkeypatch.setattr(
        "newsr.providers.llm.client.current_datetime_prompt_value",
        lambda: "2026-06-26 15:04:05 CEST",
    )
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "summary"}}]}),
    ]
    client = OpenAILLMClient(make_config())

    result = client.summarize("Headline", "Translated article")

    assert result == "summary"
    payload = json.loads(FakeHTTPConnection.requests[0]["body"].decode("utf-8"))
    system_prompt = payload["messages"][0]["content"]
    assert payload["model"] == "summary"
    assert "Summarize the article 'Headline' in Russian." in system_prompt
    assert "Current local date and time: 2026-06-26 15:04:05 CEST." in system_prompt
    assert payload["messages"][1]["content"] == "Translated article"


def test_llm_client_article_qa_prompts_include_supplied_current_datetime() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse({"choices": [{"message": {"content": "search query"}}]}),
        FakeResponse({"choices": [{"message": {"content": "answer"}}]}),
    ]
    client = OpenAILLMClient(make_config())
    current_datetime = "2026-06-26 15:04:05 CEST"

    query = client.build_article_question_query(
        "Headline",
        "Article body",
        "What happens next year?",
        current_datetime,
        [("Earlier?", "Earlier answer")],
    )
    answer = client.answer_article_question(
        "Headline",
        "Article body",
        "What happens next year?",
        current_datetime,
        [("Earlier?", "Earlier answer")],
        [SearchResult(title="Context", url="https://example.com", snippet="Snippet")],
    )

    assert query == "search query"
    assert answer == "answer"
    first_payload = json.loads(FakeHTTPConnection.requests[0]["body"].decode("utf-8"))
    second_payload = json.loads(FakeHTTPConnection.requests[1]["body"].decode("utf-8"))
    assert f"Current local date and time: {current_datetime}." in first_payload["messages"][0]["content"]
    assert f"Current local date and time: {current_datetime}." in second_payload["messages"][0]["content"]


def test_llm_client_transliterate_terms_parses_json_mapping() -> None:
    FakeHTTPConnection.plan = [
        FakeResponse(
            {"choices": [{"message": {"content": '```json\n{"Elon Musk": " илон маск ", "Ultra": 3, "Boox": ""}\n```'}}]}
        ),
    ]
    client = OpenAILLMClient(make_config())

    result = client.transliterate_terms(["Elon Musk", "Ultra", "Boox"])

    assert result == {"Elon Musk": "илон маск"}
    payload = json.loads(FakeHTTPConnection.requests[0]["body"].decode("utf-8"))
    assert payload["model"] == "translate"
    assert "Cyrillic" in payload["messages"][0]["content"]
    assert payload["messages"][1]["content"] == "Elon Musk\nUltra\nBoox"


def test_llm_client_transliterate_terms_returns_empty_mapping_for_non_json_answer() -> None:
    FakeHTTPConnection.plan = [FakeResponse({"choices": [{"message": {"content": "no idea"}}]})]
    client = OpenAILLMClient(make_config())

    assert client.transliterate_terms(["Etched"]) == {}
