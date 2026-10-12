from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from textual.widgets import DataTable, Static

from newsr.domain import ArticleContent
from newsr.ui import NewsReaderApp, QuickNavScreen

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import article_pane, body_source


def quick_nav_screen(app: NewsReaderApp) -> QuickNavScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, QuickNavScreen):
            return screen
    return None


def quick_nav_table(app: NewsReaderApp) -> DataTable:
    screen = quick_nav_screen(app)
    assert screen is not None
    return screen.query_one("#quick-nav-table", DataTable)


def quick_nav_rows(app: NewsReaderApp) -> list[list[str]]:
    table = quick_nav_table(app)
    rows: list[list[str]] = []
    for row_index in range(table.row_count):
        row = table.get_row_at(row_index)
        rows.append([str(cell) for cell in row])
    return rows


def quick_nav_selection_text(app: NewsReaderApp) -> str:
    screen = quick_nav_screen(app)
    assert screen is not None
    return str(screen.query_one("#quick-nav-selection", Static).content)


def test_ui_quick_nav_preserves_order_and_filters_missing_titles(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    hidden_article = ArticleContent(
        article_id="test-0",
        provider_id="bbc",
        provider_article_id="test-0",
        url="https://www.bbc.com/news/test-0",
        category="business",
        title="Hidden title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 3, tzinfo=UTC),
        body="Hidden source text",
    )
    appended_article = ArticleContent(
        article_id="test-2",
        provider_id="bbc",
        provider_article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Appended title",
        author="Reporter",
        published_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        body="Appended source text",
    )
    app.storage.upsert_article_source(hidden_article)
    app.storage.update_translation(hidden_article.article_id, None, "Hidden text", "done")
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.upsert_article_source(appended_article)
    app.storage.update_translation(appended_article.article_id, "Appended translated title", "Appended text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            screen = quick_nav_screen(app)
            assert screen is not None

            table = quick_nav_table(app)
            rows = quick_nav_rows(app)
            assert table.row_count == 2
            assert rows == [
                ["", "2026-03-25", "Older translated title", "BBC News", "world"],
                ["", "2026-03-20", "Appended translated title", "BBC News", "technology"],
            ]
            assert table.cursor_row == 0
            assert quick_nav_selection_text(app) == "Selected 1 of 2"

    asyncio.run(runner())


def test_ui_quick_nav_enter_opens_selected_article_and_escape_closes_without_changing_selection(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    newer_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Newer title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Newer source text",
    )
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id

            await pilot.press("l", "down", "enter")
            await pilot.pause()

            assert quick_nav_screen(app) is None
            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id
            assert body_source(app) == "Newer text"

            await pilot.press("l", "escape")
            await pilot.pause()

            assert quick_nav_screen(app) is None
            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id

    asyncio.run(runner())


def test_ui_reader_navigation_still_works_after_quick_nav(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    newer_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Newer title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Newer source text",
    )
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(200))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Older translated title", tall_body, "done")
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l", "escape")
            await pilot.pause()

            pane = article_pane(app)
            await pilot.press("pagedown")
            await pilot.pause()
            assert pane.scroll_target_y > 0

            await pilot.press("right")
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id

    asyncio.run(runner())


def test_ui_quick_nav_updates_selected_counter_when_cursor_moves(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    for index in range(3):
        article = ArticleContent(
            article_id=f"test-{index + 1}",
            url=f"https://www.bbc.com/news/test-{index + 1}",
            category="world" if index == 0 else "technology",
            title=f"Title {index + 1}",
            author="Reporter",
            published_at=datetime(2026, 3, 25, 12, index, tzinfo=UTC),
            body=f"Source text {index + 1}",
        )
        app.storage.upsert_article_source(article)
        app.storage.update_translation(article.article_id, f"Translated title {index + 1}", "Text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            assert quick_nav_selection_text(app) == "Selected 1 of 3"

            await pilot.press("down", "down")
            await pilot.pause()

            assert quick_nav_selection_text(app) == "Selected 3 of 3"

    asyncio.run(runner())


def test_ui_quick_nav_falls_back_to_first_visible_row_when_current_article_is_filtered_out(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    current_hidden_article = ArticleContent(
        article_id="test-1",
        provider_id="bbc",
        provider_article_id="test-1",
        url="https://www.bbc.com/news/test-1",
        category="world",
        title="Hidden current title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Hidden current source text",
    )
    visible_article = ArticleContent(
        article_id="test-2",
        provider_id="bbc",
        provider_article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Visible title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Visible source text",
    )
    app.storage.upsert_article_source(current_hidden_article)
    app.storage.update_translation(current_hidden_article.article_id, None, "Hidden text", "done")
    app.storage.upsert_article_source(visible_article)
    app.storage.update_translation(visible_article.article_id, "Visible translated title", "Visible text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == current_hidden_article.article_id

            await pilot.press("l")
            await pilot.pause()

            table = quick_nav_table(app)
            rows = quick_nav_rows(app)
            assert table.row_count == 1
            assert table.cursor_row == 0
            assert rows == [["", "2026-03-25", "Visible translated title", "BBC News", "technology"]]
            assert quick_nav_selection_text(app) == "Selected 1 of 1"

    asyncio.run(runner())


def test_ui_quick_nav_trims_long_titles_to_available_width(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    long_title = "Translated title " + ("x" * 80)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, long_title, "Translated text", "done")

    async def runner() -> None:
        async with app.run_test(size=(50, 20)) as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            rows = quick_nav_rows(app)
            assert len(rows) == 1
            assert rows[0][2].endswith("...")
            assert len(rows[0][2]) <= 12

    asyncio.run(runner())


def test_ui_quick_nav_falls_back_to_provider_id_when_display_name_is_unknown(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    article = ArticleContent(
        article_id="unknown:test-1",
        provider_id="unknown",
        provider_article_id="test-1",
        url="https://example.com/test-1",
        category="alerts",
        title="Unknown provider title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Unknown provider source text",
    )
    app.storage.upsert_article_source(article)
    app.storage.update_translation(article.article_id, "Unknown translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            rows = quick_nav_rows(app)
            assert rows == [[">", "2026-03-25", "Unknown translated title", "unknown", "alerts"]]

    asyncio.run(runner())


def test_ui_quick_nav_shows_empty_state_when_no_translated_titles_are_available(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, None, "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            screen = quick_nav_screen(app)
            assert screen is not None
            table = quick_nav_table(app)
            empty = screen.query_one("#quick-nav-empty", Static)
            assert table.display is False
            assert empty.display is True
            assert empty.content == "No translated articles available."
            assert quick_nav_selection_text(app) == "Selected 0 of 0"

    asyncio.run(runner())


def test_ui_quick_nav_table_shows_visible_scrollbar_styles(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    for index in range(20):
        article = ArticleContent(
            article_id=f"test-{index + 1}",
            url=f"https://www.bbc.com/news/test-{index + 1}",
            category="world",
            title=f"Title {index + 1}",
            author="Reporter",
            published_at=datetime(2026, 3, 25, 12, index, tzinfo=UTC),
            body=f"Source text {index + 1}",
        )
        app.storage.upsert_article_source(article)
        app.storage.update_translation(article.article_id, f"Translated title {index + 1}", "Text", "done")

    async def runner() -> None:
        async with app.run_test(size=(50, 12)) as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            table = quick_nav_table(app)
            styles = table.styles
            assert styles.scrollbar_visibility == "visible"
            assert styles.scrollbar_gutter == "stable"

    asyncio.run(runner())


def test_ui_quick_nav_renders_markup_characters_in_titles_literally(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Title [/bold] and [Video]", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            assert quick_nav_rows(app)[0][2] == "Title [/bold] and [Video]"

    asyncio.run(runner())
