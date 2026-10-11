from __future__ import annotations

import asyncio

import pytest

from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
from tests.ui.support.provider_home import (
    provider_home_row_index,
    provider_home_screen,
    provider_home_table,
)


@pytest.mark.provider_home
def test_ui_provider_home_provider_scope_filters_articles_and_escape_returns_home(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body", minute=0)
    tech_article_id = seed_provider_article(
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
            assert [article.provider_id for article in app.articles] == ["techcrunch"]
            assert app.current_article is not None
            assert app.current_article.article_id == tech_article_id

            await pilot.press("escape")
            await pilot.pause()
            assert provider_home_screen(app) is not None
            assert provider_home_table(app).cursor_row == provider_home_row_index(app, "TechCrunch")

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_space_opens_selected_provider(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body", minute=0)
    tech_article_id = seed_provider_article(
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
            await pilot.press("space")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert [article.provider_id for article in app.articles] == ["techcrunch"]
            assert app.current_article is not None
            assert app.current_article.article_id == tech_article_id

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_reader_navigation_still_works_after_opening_provider_scope(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    first_article_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-1",
        title="BBC 1",
        body="\n\n".join(f"Paragraph {index}" for index in range(200)),
        minute=0,
    )
    second_article_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-2",
        title="BBC 2",
        body="BBC body 2",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert provider_home_screen(app) is None
            assert app.current_article is not None
            assert app.current_article.article_id == first_article_id

            await pilot.press("right")
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == second_article_id

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_scope_reader_state_is_independent(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    bbc_second = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-2",
        title="BBC 2",
        body="BBC body 2",
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=2,
    )
    tech_second = seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-2",
        title="TC 2",
        body="TC body 2",
        minute=3,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right")
            assert app.current_article is not None
            assert app.current_article.article_id == bbc_second
            await pilot.press("escape")
            await pilot.pause()

            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right")
            assert app.current_article is not None
            assert app.current_article.article_id == tech_second
            await pilot.press("escape")
            await pilot.pause()

            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == bbc_second

            assert app.storage.load_reader_state("bbc").article_id == bbc_second
            assert app.storage.load_reader_state("techcrunch").article_id == tech_second

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_first_provider_entry_does_not_inherit_all_scope_article(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    bbc_first = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-1",
        title="BBC 1",
        body="BBC body 1",
        minute=0,
    )
    bbc_second = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-2",
        title="BBC 2",
        body="BBC body 2",
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=2,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right")
            assert app.current_article is not None
            assert app.current_article.article_id == bbc_second

            await pilot.press("escape")
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert app.current_article is not None
            assert app.current_article.article_id == bbc_first
            assert app.storage.load_reader_state("bbc").article_id is None

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_scope_next_past_last_returns_home(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert provider_home_screen(app) is None

            await pilot.press("right")
            await pilot.pause()
            assert provider_home_screen(app) is not None

    asyncio.run(runner())
