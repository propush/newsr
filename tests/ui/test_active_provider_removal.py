from __future__ import annotations

import asyncio

import pytest

from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
from tests.ui.support.provider_home import (
    assert_framed_provider_home_header,
    provider_home_row_index,
    provider_home_rows,
    provider_home_screen,
    provider_home_table,
)
from tests.ui.support.screens import confirm_dialog_screen
from tests.ui.support.source_manager import (
    category_screen,
    provider_list,
    provider_row_index,
    target_list,
)


@pytest.mark.provider_home
def test_ui_disabling_active_provider_from_reader_opens_provider_home(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body", minute=0)
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert app._provider_home.active_scope_id == "techcrunch"

            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and provider_list(app).row_count and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")

            provider_list(app).move_cursor(
                row=provider_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("space")
            await pilot.press("a")
            await pilot.pause()

            assert category_screen(app) is None
            assert provider_home_screen(app) is not None
            assert app._provider_home.active_scope_id == "techcrunch"
            assert provider_home_table(app).cursor_row == 1

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_disabling_active_provider_from_source_manager_keeps_provider_home_open(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body", minute=0)
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert app._provider_home.active_scope_id == "techcrunch"

            await pilot.press("escape")
            await pilot.pause()
            assert provider_home_screen(app) is not None

            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and provider_list(app).row_count and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")

            provider_list(app).move_cursor(
                row=provider_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("space")
            await pilot.press("a")
            await pilot.pause()

            assert category_screen(app) is None
            assert provider_home_screen(app) is not None
            assert app._provider_home.active_scope_id == "techcrunch"
            rows = provider_home_rows(app)
            assert_framed_provider_home_header(rows[0][0], "Virtual")
            assert rows[1] == ["[ALL]", "1", "2"]
            assert app._provider_home.selected_scope_id == "[ALL]"
            assert rows[3] == ["BBC News", "1", "1"]
            assert provider_home_table(app).cursor_row == 1
            assert app.status_text == "sources saved"

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_deleting_active_topic_from_source_manager_keeps_provider_home_open(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )
    app.rebuild_provider_registry()
    seed_provider_article(
        app,
        provider_id="topic:openai-policy",
        provider_article_id="topic-1",
        title="Topic 1",
        body="Topic body",
        minute=0,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "OpenAI policy"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert app._provider_home.active_scope_id == "topic:openai-policy"

            await pilot.press("escape")
            await pilot.pause()
            assert provider_home_screen(app) is not None

            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and provider_list(app).row_count and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")

            provider_list(app).move_cursor(
                row=provider_row_index(app, "OpenAI policy"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("x")
            await pilot.pause()
            assert confirm_dialog_screen(app) is not None

            await pilot.press("enter")
            await pilot.pause()
            assert confirm_dialog_screen(app) is None
            assert app.storage.get_provider("topic:openai-policy") is None

            await pilot.press("a")
            await pilot.pause()

            assert category_screen(app) is None
            assert provider_home_screen(app) is not None
            assert app._provider_home.active_scope_id == "topic:openai-policy"
            rows = provider_home_rows(app)
            assert_framed_provider_home_header(rows[0][0], "Virtual")
            assert rows[1][0] == "[ALL]"
            assert app._provider_home.selected_scope_id == "[ALL]"
            assert "OpenAI policy" not in [row[0] for row in rows]
            assert provider_home_table(app).cursor_row == 1

    asyncio.run(runner())
