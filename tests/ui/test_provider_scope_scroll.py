from __future__ import annotations

import asyncio

import pytest

from newsr.domain import ViewMode
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
from tests.ui.support.provider_home import provider_home_row_index, provider_home_table
from tests.ui.support.reader import article_pane


@pytest.mark.provider_home
def test_ui_provider_scope_scroll_offset_is_independent(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(250))
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-1",
        title="BBC 1",
        body=tall_body,
        minute=0,
    )
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-2",
        title="BBC 2",
        body=tall_body,
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body=tall_body,
        minute=2,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-2",
        title="TC 2",
        body=tall_body,
        minute=3,
    )

    async def open_scope_and_scroll(pilot, display_name: str, target_offset: int) -> int:  # type: ignore[no-untyped-def]
        provider_home_table(app).move_cursor(
            row=provider_home_row_index(app, display_name),
            column=0,
            animate=False,
        )
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        pane = article_pane(app)
        assert pane.max_scroll_y >= target_offset
        pane.scroll_to(y=target_offset, animate=False)
        await pilot.pause()
        saved_offset = int(pane.scroll_y)
        await pilot.press("escape")
        await pilot.pause()
        return saved_offset

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()

            all_offset = await open_scope_and_scroll(pilot, "[ALL]", 12)
            bbc_offset = await open_scope_and_scroll(pilot, "BBC News", 28)
            tech_offset = await open_scope_and_scroll(pilot, "TechCrunch", 44)

            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "[ALL]"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert int(article_pane(app).scroll_y) == all_offset
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
            assert int(article_pane(app).scroll_y) == bbc_offset
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
            assert int(article_pane(app).scroll_y) == tech_offset

            assert app.storage.load_reader_state("[ALL]").scroll_offset == all_offset
            assert app.storage.load_reader_state("bbc").scroll_offset == bbc_offset
            assert app.storage.load_reader_state("techcrunch").scroll_offset == tech_offset

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_scope_restores_full_scroll_after_visiting_summary_scope(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(250))
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-1",
        title="BBC 1",
        body=tall_body,
        minute=0,
    )
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-2",
        title="BBC 2",
        body=tall_body,
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body=tall_body,
        minute=2,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-2",
        title="TC 2",
        body=tall_body,
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
            bbc_pane = article_pane(app)
            assert bbc_pane.max_scroll_y >= 28
            bbc_pane.scroll_to(y=28, animate=False)
            await pilot.pause()
            saved_bbc_offset = int(bbc_pane.scroll_y)
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
            await pilot.press("s")
            await pilot.pause()
            assert app.reader_state.view_mode == ViewMode.SUMMARY
            await pilot.press("escape")
            await pilot.pause()

            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            for _ in range(3):
                await pilot.pause()

            assert app.reader_state.view_mode == ViewMode.FULL
            assert int(article_pane(app).scroll_y) == saved_bbc_offset
            assert app.storage.load_reader_state("bbc").scroll_offset == saved_bbc_offset
            assert app.storage.load_reader_state("bbc").view_mode == ViewMode.FULL
            assert app.storage.load_reader_state("techcrunch").view_mode == ViewMode.SUMMARY

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_scope_retries_scroll_restore_after_delayed_layout(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(300))
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-1",
        title="BBC 1",
        body=tall_body,
        minute=0,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body=tall_body,
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
            pane = article_pane(app)
            assert pane.max_scroll_y >= 120
            pane.scroll_to(y=120, animate=False)
            await pilot.pause()
            saved_bbc_offset = int(pane.scroll_y)
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
            await pilot.press("s")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            delayed_restore_calls = 0
            original_scroll_to = pane.scroll_to

            def delayed_scroll_to(*args, **kwargs):  # type: ignore[no-untyped-def]
                nonlocal delayed_restore_calls
                target = kwargs.get("y")
                if target is None and len(args) > 1:
                    target = args[1]
                if target == saved_bbc_offset and delayed_restore_calls == 0:
                    delayed_restore_calls += 1
                    return None
                return original_scroll_to(*args, **kwargs)

            pane.scroll_to = delayed_scroll_to  # type: ignore[method-assign]
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            for _ in range(4):
                await pilot.pause()

            assert delayed_restore_calls == 1
            assert int(article_pane(app).scroll_y) == saved_bbc_offset

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_scope_restores_after_late_scroll_reset(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(300))
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-1",
        title="BBC 1",
        body=tall_body,
        minute=0,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body=tall_body,
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
            pane = article_pane(app)
            assert pane.max_scroll_y >= 120
            pane.scroll_to(y=120, animate=False)
            await pilot.pause()
            saved_bbc_offset = int(pane.scroll_y)
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
            await pilot.press("s")
            await pilot.pause()
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
            app.set_timer(0.02, lambda: article_pane(app).scroll_to(y=0, animate=False))
            for _ in range(8):
                await pilot.pause()

            assert int(article_pane(app).scroll_y) == saved_bbc_offset

    asyncio.run(runner())
