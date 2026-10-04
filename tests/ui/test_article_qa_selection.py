from __future__ import annotations

import asyncio

import pytest
from textual.geometry import Offset
from textual.selection import Selection
from textual.widgets import Input, Markdown
from textual.widgets._markdown import MarkdownParagraph

from newsr.ui import ArticleQuestionScreen, NewsReaderApp


@pytest.fixture
def selection_app(app_config, tmp_path, article_content, monkeypatch):
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Title", "Before Привет 🌍 after\n\nSecond paragraph", "done"
    )
    monkeypatch.setattr(app._refresh, "run_due_refresh_if_idle", lambda: None)
    copies = []
    requests = []
    monkeypatch.setattr(app, "copy_to_clipboard", copies.append)
    monkeypatch.setattr(app._article_qa, "_start_request", lambda *args: requests.append(args))
    return app, copies, requests


@pytest.mark.parametrize("selection_kind", ["partial", "paragraphs", "whitespace"])
@pytest.mark.parametrize("origin", ["reader", "more_info"])
def test_question_prefills_selected_text_and_typing_appends(selection_app, selection_kind, origin) -> None:
    app, copies, requests = selection_app

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            if origin == "more_info":
                assert app.current_article is not None
                screen = app._more_info._ensure_screen(app.current_article)
                screen.set_content("Before Привет 🌍 after\n\nSecond paragraph")
                await pilot.pause()
                body = screen.query_one("#more-info-body", Markdown)
            else:
                body = app.query_one("#article-body", Markdown)
            paragraphs = list(body.query(MarkdownParagraph))
            if selection_kind == "paragraphs":
                app.screen.selections = {paragraph: Selection(None, None) for paragraph in paragraphs}
            else:
                start, end = (6, 16) if selection_kind == "partial" else (15, 16)
                app.screen.selections = {paragraphs[0]: Selection(Offset(start, 0), Offset(end, 0))}
            await pilot.pause()
            expected = app.screen.get_selected_text()
            assert expected
            if selection_kind == "partial":
                assert expected == " Привет 🌍 "
            elif selection_kind == "paragraphs":
                assert "\n" in expected and "Second paragraph" in expected
            else:
                assert expected == " "

            if origin == "more_info":
                app.action_show_article_qa()
            else:
                await pilot.press("?")
            await pilot.pause()
            assert isinstance(app.screen, ArticleQuestionScreen)
            field = app.screen.query_one("#article-qa-input", Input)
            assert field.value == expected
            assert app.focused is field
            assert field.cursor_position == len(expected)
            assert field.selection.is_empty
            await pilot.press("x")
            assert field.value == expected + "x"
            assert copies == []
            assert app.clipboard == ""
            assert requests == []

    asyncio.run(runner())


def test_question_without_selection_starts_empty_and_focused(selection_app) -> None:
    app, copies, requests = selection_app

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.screen.get_selected_text() is None
            await pilot.press("?")
            await pilot.pause()
            assert isinstance(app.screen, ArticleQuestionScreen)
            field = app.screen.query_one("#article-qa-input", Input)
            assert field.value == ""
            assert app.focused is field
            assert field.cursor_position == 0
            await pilot.press("x")
            assert field.value == "x"
            app.action_show_article_qa()
            await pilot.pause()
            assert field.value == "x"
            assert copies == []
            assert requests == []

    asyncio.run(runner())
