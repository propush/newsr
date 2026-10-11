from __future__ import annotations

import asyncio
from types import MethodType

from textual.widgets import Static

from newsr.cancellation import RefreshCancellation
from newsr.providers.llm import OpenAILLMClient
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import header_text


class FakeCategorizationLLM:
    def __init__(self, responses: list[tuple[str, ...]] | None = None) -> None:
        self.responses = responses or [("SCIENCE", "TECHNOLOGIES")]
        self.calls: list[tuple[str, str]] = []

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        return None

    def classify_article_categories(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> tuple[str, ...]:
        self.calls.append((article_title, article_text))
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]


def test_ui_manual_classification_updates_header_and_storage(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeCategorizationLLM([("SCIENCE", "TECHNOLOGIES"), ("BUSINESS",)])
    app.llm_client = llm  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "[TECHNOLOGIES]" not in header_text(app)

            await pilot.press("k")
            for _ in range(20):
                await pilot.pause()
                stored = app.storage.get_article(article_content.article_id)
                if stored is not None and stored.categories == ("TECHNOLOGIES", "SCIENCE"):
                    break
            else:
                raise AssertionError("manual classification did not finish")

            header_renderable = app.query_one("#article-header", Static).content
            assert "Article # 1 of 1  [TECHNOLOGIES] [SCIENCE]" in header_text(app)
            assert llm.calls == [(article_content.title, article_content.body)]
            assert getattr(header_renderable, "spans", [])

            await pilot.press("k")
            for _ in range(20):
                await pilot.pause()
                stored = app.storage.get_article(article_content.article_id)
                if stored is not None and stored.categories == ("BUSINESS",):
                    break
            else:
                raise AssertionError("manual reclassification did not finish")

            assert "[BUSINESS]" in header_text(app)
            assert "[SCIENCE]" not in header_text(app)

    asyncio.run(runner())


def test_ui_manual_classification_retries_empty_result_until_it_gets_a_label(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = OpenAILLMClient(app_config)
    raw_responses = iter(["[]", "[\"SCIENCE\"]"])
    llm._chat = MethodType(lambda self, model, system_prompt, content, cancellation=None: next(raw_responses), llm)  # type: ignore[method-assign]
    app.llm_client = llm  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("k")
            for _ in range(20):
                await pilot.pause()
                stored = app.storage.get_article(article_content.article_id)
                if stored is not None and stored.categories == ("SCIENCE",):
                    break
            else:
                raise AssertionError("manual classification retry did not finish")

            assert "[SCIENCE]" in header_text(app)

    asyncio.run(runner())
