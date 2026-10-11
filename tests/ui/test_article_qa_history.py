from __future__ import annotations

import asyncio

from newsr.cancellation import RefreshCancellation
from newsr.providers.search import SearchResult
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.fakes import FakeArticleQALLM, FakeSearchClient
from tests.ui.support.screens import article_qa_body, article_qa_input


class FlakyArticleQALLM(FakeArticleQALLM):
    def __init__(self, *, answer_failures: set[int], answers: list[str] | None = None) -> None:
        super().__init__(answers=answers)
        self.answer_failures = answer_failures

    def answer_article_question(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        answer_call_number = len(self.answer_calls) + 1
        if answer_call_number in self.answer_failures:
            self.answer_calls.append(
                (article_title, article_text, question, current_datetime, list(chat_history), list(search_results))
            )
            raise RuntimeError(f"synthetic failure {answer_call_number}")
        return super().answer_article_question(
            article_title,
            article_text,
            question,
            current_datetime,
            chat_history,
            search_results,
            cancellation,
        )


def test_ui_article_qa_follow_up_uses_prior_turns(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeArticleQALLM(answers=["Answer 1", "Answer 2"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()

            article_qa_input(app).value = "First question?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer 1" in article_qa_body(app):
                    break

            article_qa_input(app).value = "And now?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer 2" in article_qa_body(app):
                    break

            body = article_qa_body(app)
            assert "First question?" in body
            assert "Answer 1" in body
            assert "And now?" in body
            assert "Answer 2" in body
            assert llm.query_calls[1][4] == [("First question?", "Answer 1")]
            assert llm.answer_calls[1][4] == [("First question?", "Answer 1")]

    asyncio.run(runner())


def test_ui_article_qa_recalls_questions_and_restores_draft(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.llm_client = FakeArticleQALLM(answers=["Answer 1", "Answer 2"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient([])  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()

            await pilot.press("up", "down")
            assert article_qa_input(app).value == ""

            for question, expected_answer in [
                ("First question?", "Answer 1"),
                ("Second question?", "Answer 2"),
            ]:
                article_qa_input(app).value = question
                await pilot.press("enter")
                for _ in range(20):
                    await pilot.pause()
                    if expected_answer in article_qa_body(app):
                        break

            article_qa_input(app).value = "Unfinished draft"
            await pilot.press("up")
            assert article_qa_input(app).value == "Second question?"
            await pilot.press("up", "up")
            assert article_qa_input(app).value == "First question?"
            await pilot.press("down")
            assert article_qa_input(app).value == "Second question?"
            await pilot.press("down", "down")
            assert article_qa_input(app).value == "Unfinished draft"

            await pilot.press("up")
            article_qa_input(app).value = "Revised draft"
            await pilot.press("down")
            assert article_qa_input(app).value == "Revised draft"
            await pilot.press("up", "down")
            assert article_qa_input(app).value == "Revised draft"

    asyncio.run(runner())


def test_ui_article_qa_third_turn_uses_full_answered_history(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeArticleQALLM(answers=["Answer 1", "Answer 2", "Answer 3"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()

            for question, expected_answer in [
                ("First question?", "Answer 1"),
                ("Second question?", "Answer 2"),
                ("Third question?", "Answer 3"),
            ]:
                article_qa_input(app).value = question
                await pilot.press("enter")
                for _ in range(20):
                    await pilot.pause()
                    if expected_answer in article_qa_body(app):
                        break

            assert llm.query_calls[2][4] == [
                ("First question?", "Answer 1"),
                ("Second question?", "Answer 2"),
            ]
            assert llm.answer_calls[2][4] == [
                ("First question?", "Answer 1"),
                ("Second question?", "Answer 2"),
            ]

    asyncio.run(runner())


def test_ui_article_qa_failed_turn_is_excluded_from_follow_up_history(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FlakyArticleQALLM(answer_failures={2}, answers=["Answer 1", "Answer 3"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()

            article_qa_input(app).value = "First question?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer 1" in article_qa_body(app):
                    break

            article_qa_input(app).value = "This one fails?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer unavailable" in article_qa_body(app):
                    break

            article_qa_input(app).value = "What about now?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer 3" in article_qa_body(app):
                    break

            assert llm.query_calls[2][4] == [("First question?", "Answer 1")]
            assert llm.answer_calls[2][4] == [("First question?", "Answer 1")]
            await pilot.press("up")
            assert article_qa_input(app).value == "What about now?"
            await pilot.press("up")
            assert article_qa_input(app).value == "This one fails?"

    asyncio.run(runner())
