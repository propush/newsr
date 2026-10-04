from __future__ import annotations

import asyncio
import base64
from threading import Event

import pytest
from textual.geometry import Offset
from textual.selection import Selection
from textual.widgets import Input, Markdown, Static
from textual.widgets._markdown import MarkdownParagraph

from newsr.export import ClipboardError
from newsr.ui import ArticleQuestionScreen, BriefReaderScreen, MoreInfoScreen, NewsReaderApp
from newsr.ui.screens.help import HelpScreen


@pytest.fixture
def clipboard_app(app_config, tmp_path, article_content, monkeypatch):
    for name in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"):
        monkeypatch.delenv(name, raising=False)
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Title", "Before Привет after\n\nSecond paragraph", "done")
    monkeypatch.setattr(app._refresh, "run_due_refresh_if_idle", lambda: None)
    copies = []
    monkeypatch.setattr(app._clipboard_controller.clipboard, "copy_text", copies.append)
    return app, copies


async def wait_for_copy(app: NewsReaderApp) -> None:
    worker = app._clipboard_controller._worker
    if worker is not None:
        await worker.wait()


@pytest.mark.parametrize("key", ["ctrl+c", "super+c", "ctrl+shift+c"])
def test_reader_copies_only_selected_rendered_text(clipboard_app, key) -> None:
    app, copies = clipboard_app

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            paragraph = app.query_one("#article-body", Markdown).query(MarkdownParagraph).first()
            selection = Selection(Offset(7, 0), Offset(13, 0))
            app.screen.selections = {paragraph: selection}
            await pilot.pause()
            focus, index, mode = app.focused, app.current_index, app.active_reader_state.view_mode
            scroll = app.query_one("#article-pane").scroll_offset
            await pilot.press(key)
            await wait_for_copy(app)
            assert copies == ["Привет"]
            assert app.clipboard == "Привет"
            assert app.screen.selections == {paragraph: selection}
            assert (app.focused, app.current_index, app.active_reader_state.view_mode) == (focus, index, mode)
            assert app.query_one("#article-pane").scroll_offset == scroll

    asyncio.run(runner())


@pytest.mark.parametrize("screen_kind", ["more_info", "qa", "brief", "help"])
def test_copy_in_modal_preserves_screen_and_focus(clipboard_app, screen_kind) -> None:
    app, copies = clipboard_app

    async def runner() -> None:
        async with app.run_test() as pilot:
            if screen_kind == "more_info":
                screen = MoreInfoScreen(app.ui, "Title")
                screen.body_text = "Привет 🌍\n\nSecond paragraph"
            elif screen_kind == "qa":
                screen = ArticleQuestionScreen(app.ui, "Title")
                screen.body_text = "Привет 🌍\n\nSecond paragraph"
            elif screen_kind == "brief":
                screen = BriefReaderScreen(app.ui, "Привет 🌍\n\nSecond paragraph")
            else:
                screen = HelpScreen("Привет 🌍\nsecond line")
            app.push_screen(screen)
            await pilot.pause()
            if screen_kind == "help":
                widgets = [screen.query_one("#help-text", Static)]
            else:
                widgets = list(screen.query(MarkdownParagraph))
            screen.selections = {widget: Selection(None, None) for widget in widgets}
            await pilot.pause()
            expected = screen.get_selected_text()
            assert expected and "Привет 🌍" in expected and "\n" in expected
            focus = app.focused
            await pilot.press("ctrl+c")
            await wait_for_copy(app)
            assert copies == [expected]
            assert app.screen is screen
            assert app.focused is focus

    asyncio.run(runner())


@pytest.mark.parametrize("key", ["ctrl+c", "super+c", "ctrl+shift+c"])
def test_focused_input_selection_takes_precedence(clipboard_app, key) -> None:
    app, copies = clipboard_app

    async def runner() -> None:
        async with app.run_test() as pilot:
            screen = ArticleQuestionScreen(app.ui, "Title")
            app._article_qa._screen = screen
            app.push_screen(screen)
            await pilot.pause()
            screen.set_sources([("Source", "https://example.com")])
            await pilot.pause()
            field = screen.query_one(Input)
            field.value = "before Привет after"
            field.selection = (7, 13)
            screen.selections = {screen.query_one("#article-qa-header", Static): Selection(None, None)}
            await pilot.press(key)
            await wait_for_copy(app)
            assert copies == ["Привет"]
            assert field.value == "before Привет after"
            assert field.selection == (7, 13)
            await pilot.press("tab")
            assert app.focused is not field
            await pilot.press("escape")
            assert app.screen is not screen

    asyncio.run(runner())


def test_selection_alone_and_copy_without_selection_leave_clipboard_unchanged(clipboard_app) -> None:
    app, copies = clipboard_app

    async def runner() -> None:
        async with app.run_test() as pilot:
            paragraph = app.query_one(MarkdownParagraph)
            app.screen.selections = {paragraph: Selection(None, None)}
            await pilot.pause()
            assert copies == []
            app.screen.clear_selection()
            await pilot.press("ctrl+c")
            assert copies == []
            assert app.clipboard == ""
            app.push_screen(HelpScreen("help"))
            await pilot.pause()
            await pilot.press("ctrl+c")
            assert not isinstance(app.screen, HelpScreen)

    asyncio.run(runner())


def test_binding_rebuild_keeps_copy_shortcuts(clipboard_app) -> None:
    app, copies = clipboard_app

    async def runner() -> None:
        async with app.run_test() as pilot:
            for home_open in (True, False):
                app._set_provider_home_footer_bindings(provider_home_open=home_open)
                paragraph = app.query_one(MarkdownParagraph)
                app.screen.selections = {paragraph: Selection(None, None)}
                await pilot.press("ctrl+c")
                await wait_for_copy(app)
            assert len(copies) == 2

    asyncio.run(runner())


@pytest.mark.parametrize("ssh_variable", ["SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY"])
def test_ssh_copy_uses_terminal_and_internal_clipboards(clipboard_app, monkeypatch, ssh_variable) -> None:
    app, copies = clipboard_app
    monkeypatch.setenv(ssh_variable, "ssh-session")

    async def runner() -> None:
        async with app.run_test() as pilot:
            writes = []
            monkeypatch.setattr(app._driver, "write", writes.append)
            app.copy_to_clipboard("Привет 🌍")
            assert app.clipboard == "Привет 🌍"
            assert copies == []
            encoded = base64.b64encode("Привет 🌍".encode()).decode()
            assert f"\x1b]52;c;{encoded}\a" in writes

    asyncio.run(runner())


def test_native_failure_preserves_internal_clipboard_and_modal(clipboard_app, monkeypatch) -> None:
    app, copies = clipboard_app
    notifications = []

    def fail(text):
        raise ClipboardError("pbcopy timed out")

    monkeypatch.setattr(app._clipboard_controller.clipboard, "copy_text", fail)
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: notifications.append((message, kwargs)))

    async def runner() -> None:
        async with app.run_test() as pilot:
            screen = HelpScreen("selected text")
            app.push_screen(screen)
            await pilot.pause()
            screen.selections = {screen.query_one(Static): Selection(None, None)}
            await pilot.press("ctrl+c")
            await wait_for_copy(app)
            assert app.screen is screen
            assert app.clipboard == "selected text"
            assert len(notifications) == 1
            assert "pbcopy timed out" in notifications[0][0]
            assert notifications[0][1]["severity"] == "warning"

    asyncio.run(runner())


def test_native_writes_are_serialized_without_blocking_ui(clipboard_app, monkeypatch) -> None:
    app, copies = clipboard_app
    started, release = Event(), Event()

    def copy(text):
        if text == "first":
            started.set()
            assert release.wait(timeout=2)
        copies.append(text)

    monkeypatch.setattr(app._clipboard_controller.clipboard, "copy_text", copy)

    async def runner() -> None:
        async with app.run_test() as pilot:
            app.copy_to_clipboard("first")
            assert await asyncio.to_thread(started.wait, 1)
            try:
                app.copy_to_clipboard("second")
                app.copy_to_clipboard("third")
                await pilot.press("h")
                assert isinstance(app.screen, HelpScreen)
                assert copies == []
            finally:
                release.set()
            await wait_for_copy(app)
            assert copies == ["first", "second", "third"]
            app._clipboard_controller.shutdown()
            app.copy_to_clipboard("after shutdown")
            assert copies == ["first", "second", "third"]

    asyncio.run(runner())
