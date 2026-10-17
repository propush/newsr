from __future__ import annotations

import asyncio
import webbrowser
from threading import Thread

from textual.widgets import Static

from newsr.cancellation import RefreshCancellation
from newsr.providers.search import SearchChallengeError
from newsr.ui import MoreInfoScreen, NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.fakes import FakeMoreInfoLLM
from tests.ui.support.reader import body_source
from tests.ui.support.screens import article_qa_input, article_qa_screen, more_info_body, more_info_screen

CHECK_URL = "https://duckduckgo.com/?q=example+query"


class ChallengingSearchClient:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self.calls = 0

    def search(self, query: str, limit: int = 5, cancellation: RefreshCancellation | None = None, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        self._app._offer_search_check_from_thread(CHECK_URL)
        raise SearchChallengeError(
            "DuckDuckGo search is unavailable because DuckDuckGo returned an anti-bot challenge page (HTTP 202).",
            browser_url=CHECK_URL,
        )


def build_app(app_config, tmp_path, article_content, monkeypatch):  # type: ignore[no-untyped-def]
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    notifications: list[tuple[str, dict]] = []
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append((message, kwargs)))
    opened_urls: list[tuple[str, int]] = []

    def fake_open(url: str, new: int = 0) -> bool:
        opened_urls.append((url, new))
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)
    return app, notifications, opened_urls


async def wait_for(pilot, condition) -> None:  # type: ignore[no-untyped-def]
    for _ in range(40):
        if condition():
            return
        await pilot.pause()
    assert condition()


def status_text(app: NewsReaderApp) -> str:
    return str(app.query_one("#status", Static).content)


def test_ui_challenge_from_worker_thread_shows_toast_without_blocking_reader(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    app, notifications, opened_urls = build_app(app_config, tmp_path, article_content, monkeypatch)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            stack_size = len(app.screen_stack)
            focused = app.focused

            worker = Thread(target=app._offer_search_check_from_thread, args=(CHECK_URL,))
            worker.start()
            await wait_for(pilot, lambda: bool(notifications))
            worker.join(timeout=5)

            message, options = notifications[0]
            assert "Ctrl+O" in message
            assert options["severity"] == "warning"
            assert len(app.screen_stack) == stack_size
            assert app.focused is focused
            assert opened_urls == []

            await pilot.press("s")
            await pilot.pause()
            assert body_source(app) == "Summary text"

    asyncio.run(runner())


def test_ui_ctrl_o_opens_pending_check_once_and_reports_status(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    app, _notifications, opened_urls = build_app(app_config, tmp_path, article_content, monkeypatch)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            app.offer_search_check(CHECK_URL)

            await pilot.press("ctrl+o")
            await wait_for(pilot, lambda: status_text(app) == "opened DuckDuckGo check in browser")
            assert opened_urls == [(CHECK_URL, 2)]

            await pilot.press("ctrl+o")
            await wait_for(pilot, lambda: status_text(app) == "no pending DuckDuckGo check")
            assert opened_urls == [(CHECK_URL, 2)]

    asyncio.run(runner())


def test_ui_more_info_challenge_shows_error_and_toast_and_ctrl_o_works_over_overlay(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    app, notifications, opened_urls = build_app(app_config, tmp_path, article_content, monkeypatch)
    app.llm_client = FakeMoreInfoLLM()  # type: ignore[assignment]
    search = ChallengingSearchClient(app)
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            await wait_for(
                pilot,
                lambda: more_info_screen(app) is not None and "More info unavailable" in more_info_body(app),
            )

            assert "anti-bot challenge" in more_info_body(app)
            assert search.calls == 1
            assert len(notifications) == 1
            assert isinstance(app.screen, MoreInfoScreen)

            await pilot.press("ctrl+o")
            await wait_for(pilot, lambda: bool(opened_urls))
            assert opened_urls == [(CHECK_URL, 2)]
            assert isinstance(app.screen, MoreInfoScreen)

    asyncio.run(runner())


def test_ui_ctrl_o_keeps_article_qa_question_while_opening_check(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    app, _notifications, opened_urls = build_app(app_config, tmp_path, article_content, monkeypatch)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            await pilot.press("w", "h", "y")
            app.offer_search_check(CHECK_URL)

            await pilot.press("ctrl+o")
            await wait_for(pilot, lambda: bool(opened_urls))

            assert opened_urls == [(CHECK_URL, 2)]
            assert article_qa_screen(app) is app.screen
            assert article_qa_input(app).value == "why"
            assert app.focused is article_qa_input(app)

    asyncio.run(runner())
