from __future__ import annotations

import asyncio
import webbrowser
from threading import Event

from textual.widgets import ListView, LoadingIndicator, Markdown, Static

from newsr.cancellation import RefreshCancellation
from newsr.domain import ViewMode
from newsr.providers.search import SearchResult
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.fakes import FakeArticleQALLM, FakeSearchClient
from tests.ui.support.reader import body_source
from tests.ui.support.screens import (
    article_qa_body,
    article_qa_input,
    article_qa_screen,
    open_link_confirm_screen,
)


def article_qa_loading_indicator(app: NewsReaderApp) -> LoadingIndicator:
    screen = article_qa_screen(app)
    assert screen is not None
    return screen.query_one("#article-qa-loading", LoadingIndicator)


def article_qa_source_list(app: NewsReaderApp) -> ListView:
    screen = article_qa_screen(app)
    assert screen is not None
    return screen.query_one("#article-qa-source-list", ListView)


class BlockingArticleQALLM:
    def __init__(self) -> None:
        self.started = Event()
        self.cancelled = Event()

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        return None

    def build_article_question_query(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        assert cancellation is not None
        self.started.set()
        cancellation.cancelled_event.wait(timeout=5)
        if cancellation.is_cancelled:
            self.cancelled.set()
        cancellation.raise_if_cancelled()
        return "unused"

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
        raise AssertionError("answer_article_question should not run after cancellation")


def test_ui_opens_article_qa_overlay_and_escape_restores_summary_mode(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            assert body_source(app) == "Summary text"

            await pilot.press("?")
            await pilot.pause()

            screen = article_qa_screen(app)
            assert screen is not None
            assert "State: ready" in screen.query_one("#article-qa-header", Static).content
            assert "Nothing in this chat is saved" in article_qa_body(app)

            await pilot.press("escape")
            await pilot.pause()

            assert article_qa_screen(app) is None
            assert app.reader_state.view_mode == ViewMode.SUMMARY
            assert body_source(app) == "Summary text"

    asyncio.run(runner())


def test_ui_article_qa_submits_question_shows_answer_and_sources(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeArticleQALLM(answers=["Direct answer"])
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
            article_qa_input(app).value = "What happened?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if "Direct answer" in article_qa_body(app):
                    break

            body = article_qa_body(app)
            assert "Question 1" in body
            assert "**You:** What happened?" in body
            assert "### Answer" in body
            assert "Direct answer" in body
            assert "### Sources" in body
            assert "[Context](https://example.com/context)" in body
            assert search.calls == ["latest context"]
            assert llm.query_calls == [
                (
                    "Example title",
                    "Paragraph one.\n\nParagraph two.",
                    "What happened?",
                    llm.query_calls[0][3],
                    [],
                )
            ]
            assert llm.answer_calls[0][0] == "Example title"
            assert llm.answer_calls[0][1] == "Paragraph one.\n\nParagraph two."
            assert llm.answer_calls[0][2] == "What happened?"
            assert llm.answer_calls[0][4] == []
            assert llm.answer_calls[0][5] == [
                SearchResult(title="Context", url="https://example.com/context", snippet="Details")
            ]
            assert llm.answer_calls[0][3]

    asyncio.run(runner())


def test_ui_article_qa_source_list_opens_browser_with_keyboard(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.llm_client = FakeArticleQALLM(answers=["Direct answer"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [
            SearchResult(title="Context", url="https://example.com/context", snippet="Details"),
            SearchResult(title="Second", url="https://example.com/second", snippet="More details"),
        ]
    )
    opened_urls: list[tuple[str, int]] = []
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0: opened_urls.append((url, new)) or True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "What happened?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if "Direct answer" in article_qa_body(app):
                    break

            assert article_qa_input(app).has_focus
            await pilot.press("tab")
            await pilot.pause()
            assert article_qa_source_list(app).has_focus
            await pilot.press("down")
            assert article_qa_source_list(app).index == 1
            await pilot.press("enter")
            await pilot.pause()
            confirm = open_link_confirm_screen(app)
            assert confirm is not None
            assert "URL: https://example.com/second" in confirm.query_one("#open-link-body", Static).content
            assert opened_urls == []
            await pilot.press("enter")
            await pilot.pause()

    asyncio.run(runner())

    assert opened_urls == [("https://example.com/second", 2)]


def test_ui_article_qa_markdown_link_click_opens_browser(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.llm_client = FakeArticleQALLM(answers=["Direct answer"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    opened_urls: list[tuple[str, int]] = []
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0: opened_urls.append((url, new)) or True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "What happened?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if "Direct answer" in article_qa_body(app):
                    break

            screen = article_qa_screen(app)
            assert screen is not None
            markdown = screen.query_one("#article-qa-body", Markdown)
            screen.on_markdown_link_clicked(
                Markdown.LinkClicked(markdown, "https://example.com/новости/игры?тема=БАФТА")
            )
            await pilot.pause()
            confirm = open_link_confirm_screen(app)
            assert confirm is not None
            assert (
                "URL: https://example.com/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8/"
                "%D0%B8%D0%B3%D1%80%D1%8B?%D1%82%D0%B5%D0%BC%D0%B0=%D0%91%D0%90%D0%A4%D0%A2%D0%90"
            ) in confirm.query_one("#open-link-body", Static).content
            assert opened_urls == []
            await pilot.press("enter")
            await pilot.pause()

    asyncio.run(runner())

    assert opened_urls == [
        (
            "https://example.com/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8/"
            "%D0%B8%D0%B3%D1%80%D1%8B?%D1%82%D0%B5%D0%BC%D0%B0=%D0%91%D0%90%D0%A4%D0%A2%D0%90",
            2,
        )
    ]


def test_ui_article_qa_escape_cancels_inflight_request_and_clears_session(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = BlockingArticleQALLM()
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = FakeSearchClient([])  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "Need current context?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if llm.started.is_set() and article_qa_screen(app) is not None:
                    break

            screen = article_qa_screen(app)
            assert llm.started.is_set()
            assert screen is not None
            assert "State: asking configured llm for web search query..." in screen.query_one(
                "#article-qa-header", Static
            ).content
            assert article_qa_loading_indicator(app).display is True

            await pilot.press("escape")
            for _ in range(20):
                await pilot.pause()
                if llm.cancelled.is_set():
                    break

            assert llm.cancelled.is_set()
            assert article_qa_screen(app) is None

            await pilot.press("?")
            await pilot.pause()
            assert "Need current context?" not in article_qa_body(app)
            assert "Nothing in this chat is saved" in article_qa_body(app)
            await pilot.press("up")
            assert article_qa_input(app).value == ""

    asyncio.run(runner())


def test_ui_article_qa_does_not_persist_answers(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    app.llm_client = FakeArticleQALLM(answers=["Direct answer"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "What changed?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if "Direct answer" in article_qa_body(app):
                    break

            await pilot.press("escape")
            await pilot.pause()

    asyncio.run(runner())

    reloaded = NewsReaderApp(app_config, storage_path)
    try:
        reloaded.load_articles()
        assert reloaded.current_article is not None
        assert reloaded.current_article.more_info is None
    finally:
        reloaded.storage.close()
