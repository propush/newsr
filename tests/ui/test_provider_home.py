from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from textual.widgets import DataTable, Static

from newsr.domain import ArticleContent
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
from tests.ui.support.provider_home import (
    assert_framed_provider_home_header,
    provider_home_row_index,
    provider_home_rows,
    provider_home_screen,
    provider_home_table,
)
from tests.ui.support.reader import footer_bindings


def provider_home_row_cells(app: NewsReaderApp, row_index: int) -> list[object]:
    table = provider_home_table(app)
    return list(table.get_row_at(row_index))


def provider_home_footer_text(app: NewsReaderApp) -> str:
    return str(app.query_one("#article-url", Static).content)


def provider_home_selectable_row_index(app: NewsReaderApp, row_index: int, step: int) -> int | None:
    rows = provider_home_rows(app)
    index = row_index
    while 0 <= index < len(rows):
        row = rows[index]
        if len(row) >= 3 and row[1].isdigit() and row[2].isdigit():
            return index
        index += step
    boundary = range(len(rows)) if step < 0 else range(len(rows) - 1, -1, -1)
    for index in boundary:
        row = rows[index]
        if len(row) >= 3 and row[1].isdigit() and row[2].isdigit():
            return index
    return None


def provider_home_page_row_count(table: DataTable, row_index: int, step: int) -> int:
    page_height = table.scrollable_content_region.height - (table.header_height if table.show_header else 0)
    offset = 0
    rows_to_scroll = 0
    ordered_rows = table.ordered_rows[row_index:] if step > 0 else table.ordered_rows[: row_index + 1]
    for ordered_row in ordered_rows:
        offset += ordered_row.height
        rows_to_scroll += 1
        if offset > page_height:
            break
    return rows_to_scroll


@pytest.mark.provider_home
def test_ui_provider_home_starts_with_all_then_enabled_providers_sorted_by_unread(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-2",
        title="TC 2",
        body="TC body 2",
        minute=2,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            rows = provider_home_rows(app)
            virtual_header = provider_home_row_cells(app, 0)[0]
            providers_header = provider_home_row_cells(app, 2)[0]

            assert_framed_provider_home_header(virtual_header, "Virtual")
            assert_framed_provider_home_header(providers_header, "Providers")
            assert_framed_provider_home_header(rows[0][0], "Virtual")
            assert_framed_provider_home_header(rows[2][0], "Providers")
            assert rows[1] == ["[ALL]", "3", "3"]
            assert rows[3] == ["TechCrunch", "2", "2"]
            assert rows[4] == ["BBC News", "1", "1"]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_counts_only_translated_articles(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    pending = ArticleContent(
        article_id="bbc:pending-1",
        provider_id="bbc",
        provider_article_id="pending-1",
        url="https://example.com/bbc/pending-1",
        category="world",
        title="Pending BBC",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 1, tzinfo=UTC),
        body="Pending BBC body",
    )
    app.storage.upsert_article_source(pending)
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
            rows = provider_home_rows(app)
            assert_framed_provider_home_header(rows[0][0], "Virtual")
            assert rows[1] == ["[ALL]", "2", "2"]
            assert_framed_provider_home_header(rows[2][0], "Providers")
            assert rows[3] == ["BBC News", "1", "1"]
            assert rows[4] == ["TechCrunch", "1", "1"]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_hides_all_row_when_configured(app_config, tmp_path) -> None:
    app_config.ui.show_all = False
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-2",
        title="TC 2",
        body="TC body 2",
        minute=2,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            rows = provider_home_rows(app)
            assert len(rows) == 3
            assert_framed_provider_home_header(rows[0][0], "Providers")
            assert rows[1] == ["TechCrunch", "2", "2"]
            assert rows[2] == ["BBC News", "1", "1"]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_uses_available_width_for_provider_column(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            table = provider_home_table(app)
            provider_column = list(table.columns.values())[0]
            assert provider_column.width > 12

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_hides_header_widget(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header = app.query_one("#article-header", Static)
            assert header.display is False

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_hides_selected_provider_summary_line(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert provider_home_footer_text(app) == ""

            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()

            assert provider_home_footer_text(app) == ""

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_shows_current_app_status(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            status = app.query_one("#status", Static)
            assert str(status.content) == "ready"

            app._refresh.set_status_text("fetching BBC News: World")
            app.refresh_view()
            await pilot.pause()
            assert str(status.content) == "fetching BBC News: World"

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_forwards_ctrl_p_to_command_palette(app_config, tmp_path, monkeypatch) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    calls: list[bool] = []

    def fake_command_palette() -> None:
        calls.append(True)

    monkeypatch.setattr(app, "action_command_palette", fake_command_palette)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("ctrl+p")
            await pilot.pause()
            assert calls == [True]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_navigation_still_works_after_command_palette(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            table = provider_home_table(app)
            assert table.cursor_row == provider_home_row_index(app, "[ALL]")

            await pilot.press("ctrl+p", "escape")
            await pilot.pause()
            await pilot.press("down")
            await pilot.pause()

            assert table.cursor_row == provider_home_row_index(app, "BBC News")

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_hides_reader_only_bindings_from_footer(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert footer_bindings(app) == [
                ("b", "Brief Review", "brief_or_page_up"),
                ("c", "Sources", "show_source_manager"),
                ("w", "Watch Topic", "watch_topic"),
                ("d", "Refresh", "download_articles"),
                ("h", "Help", "show_help"),
                ("q", "Quit", "quit_reader"),
            ]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_d_forces_refresh_all_enabled_real_providers(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )
    app.rebuild_provider_registry()
    calls: list[tuple[list[str] | None, bool]] = []
    app._refresh.start = lambda provider_ids=None, *, force=False: calls.append((provider_ids, force))  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            calls.clear()
            await pilot.press("d")
            await pilot.pause()
            assert calls == [(["bbc", "topic:openai-policy"], True)]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_reader_d_forces_refresh_for_current_provider_only(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    calls: list[tuple[list[str] | None, bool]] = []
    app._refresh.start = lambda provider_ids=None, *, force=False: calls.append((provider_ids, force))  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            calls.clear()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert calls == [(["bbc"], True)]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_enter_all_opens_reader(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert provider_home_screen(app) is not None
            await pilot.press("enter")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_arrow_keys_move_between_provider_rows(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            table = provider_home_table(app)
            assert table.cursor_row == provider_home_row_index(app, "[ALL]")

            await pilot.press("down")
            await pilot.pause()
            assert table.cursor_row == provider_home_row_index(app, "BBC News")

            await pilot.press("up")
            await pilot.pause()
            assert table.cursor_row == provider_home_row_index(app, "[ALL]")

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_top_navigation_jumps_to_first_provider_row(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            table = provider_home_table(app)
            first_provider_row = provider_home_row_index(app, "[ALL]")
            last_provider_row = provider_home_row_index(app, "TechCrunch")

            table.move_cursor(row=last_provider_row, column=0, animate=False)
            await pilot.pause()
            await pilot.press("ctrl+home")
            await pilot.pause()
            assert table.cursor_row == first_provider_row

            table.move_cursor(row=last_provider_row, column=0, animate=False)
            await pilot.pause()
            await pilot.press("pageup")
            await pilot.pause()
            assert table.cursor_row == first_provider_row

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_page_keys_use_visible_page_height(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    for provider_id in app.builtin_providers:
        app.storage.set_provider_enabled(provider_id, True)

    async def runner() -> None:
        async with app.run_test(size=(70, 16)) as pilot:
            await pilot.pause()
            table = provider_home_table(app)
            start_row = provider_home_row_index(app, "[ALL]")
            rows_to_scroll = provider_home_page_row_count(table, start_row, 1)
            expected_row = provider_home_selectable_row_index(app, start_row + rows_to_scroll - 1, 1)

            assert expected_row is not None
            assert expected_row - start_row > 5

            await pilot.press("pagedown")
            await pilot.pause()
            assert table.cursor_row == expected_row

            rows_to_scroll_up = provider_home_page_row_count(table, table.cursor_row, -1)
            expected_up_row = provider_home_selectable_row_index(
                app,
                table.cursor_row - rows_to_scroll_up + 1,
                -1,
            )

            assert expected_up_row is not None

            await pilot.press("pageup")
            await pilot.pause()
            assert table.cursor_row == expected_up_row

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_hidden_all_row_does_not_break_return_to_provider_home(app_config, tmp_path, article_content) -> None:
    app_config.ui.show_all = False
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            rows = provider_home_rows(app)
            assert len(rows) == 2
            assert_framed_provider_home_header(rows[0][0], "Providers")
            assert rows[1] == ["BBC News", "1", "1"]

            app.open_scope("[ALL]")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert app._provider_home.active_scope_id == "[ALL]"
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id

            await pilot.press("escape")
            await pilot.pause()

            table = provider_home_table(app)
            rows = provider_home_rows(app)
            assert len(rows) == 2
            assert_framed_provider_home_header(rows[0][0], "Providers")
            assert rows[1] == ["BBC News", "1", "1"]
            assert table.cursor_row == 1
            assert app._provider_home.active_scope_id == "[ALL]"
            assert app._provider_home.selected_scope_id == "bbc"

    asyncio.run(runner())
