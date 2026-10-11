from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from textual.widgets import Static

from newsr.domain import ArticleContent
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import article_pane, body_source, plain_content


def test_ui_help_lists_article_qa_shortcut(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("h")
            await pilot.pause()
            help_text = plain_content(app.screen.query_one("#help-text", Static).content)
            assert "K: classify categories" in help_text
            assert "?: ask about article" in help_text

    asyncio.run(runner())


def test_ui_closing_help_with_escape_keeps_article_view(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.provider_home_open is False

            await pilot.press("s")
            await pilot.pause()
            assert body_source(app) == "Summary text"

            await pilot.press("h")
            await pilot.pause()
            assert app.screen.query_one("#help-text", Static).content

            await pilot.press("escape")
            await pilot.pause()

            assert app.provider_home_open is False
            assert len(app.screen_stack) == 1
            assert body_source(app) == "Summary text"
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id

    asyncio.run(runner())


def test_ui_reader_navigation_still_works_after_help_screen(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    second_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Second title",
        author="Reporter",
        published_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        body="Second source text",
    )
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(200))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", tall_body, "done")
    app.storage.upsert_article_source(second_article)
    app.storage.update_translation(second_article.article_id, "Second translated title", "Second text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("h", "escape")
            await pilot.pause()

            pane = article_pane(app)
            await pilot.press("pagedown")
            await pilot.pause()
            assert pane.scroll_target_y > 0

            await pilot.press("right")
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == second_article.article_id

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_help_shows_provider_only_bindings(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("h")
            await pilot.pause()
            help_text = plain_content(app.screen.query_one("#help-text", Static).content)
            assert "Enter/Space: open the selected provider" in help_text
            assert "B: brief review" in help_text
            assert "C: manage sources" in help_text
            assert "W: create watched topic" in help_text
            assert "D: force refresh all providers" in help_text
            assert "Ctrl+P: command palette / choose theme" in help_text
            assert "K: classify categories" not in help_text
            assert "Left/Right: previous/next article" not in help_text
            assert "S: cycle reader mode" not in help_text
            assert "M: more info" not in help_text
            assert "L: article list" not in help_text

    asyncio.run(runner())
