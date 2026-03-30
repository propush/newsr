from __future__ import annotations

import pytest

from newsr.providers.bbc.provider import BBCNewsProvider
from newsr.providers.llm.client import OpenAILLMClient
from newsr.providers.search.duckduckgo import DuckDuckGoSearchClient
from newsr.ui import NewsReaderApp


@pytest.fixture(autouse=True)
def isolate_ui_tests_from_live_services(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_discover_targets(
        self: BBCNewsProvider, cancellation=None
    ) -> list:  # type: ignore[no-untyped-def]
        return list(self.default_targets())

    def fake_fetch_candidates(
        self: BBCNewsProvider, target, limit, cancellation=None
    ) -> list:  # type: ignore[no-untyped-def]
        return []

    def fail_fetch_article(
        self: BBCNewsProvider, candidate, cancellation=None
    ) -> None:  # type: ignore[no-untyped-def]
        raise AssertionError("UI tests must not fetch live BBC article content")

    def fail_llm_chat(
        self: OpenAILLMClient, model, system_prompt, content, cancellation=None
    ) -> str:  # type: ignore[no-untyped-def]
        raise AssertionError("UI tests must not call the real local LLM")

    def fail_search(
        self: DuckDuckGoSearchClient, query, limit=5, cancellation=None
    ) -> list:  # type: ignore[no-untyped-def]
        raise AssertionError("UI tests must not call live DuckDuckGo search")

    monkeypatch.setattr(BBCNewsProvider, "discover_targets", fake_discover_targets)
    monkeypatch.setattr(BBCNewsProvider, "fetch_candidates", fake_fetch_candidates)
    monkeypatch.setattr(BBCNewsProvider, "fetch_article", fail_fetch_article)
    monkeypatch.setattr(OpenAILLMClient, "_chat", fail_llm_chat)
    monkeypatch.setattr(DuckDuckGoSearchClient, "search", fail_search)


@pytest.fixture(autouse=True)
def disable_provider_home_for_legacy_ui_tests(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    if request.node.get_closest_marker("provider_home") is not None:
        return
    monkeypatch.setattr(NewsReaderApp, "show_provider_home", lambda self: None)
