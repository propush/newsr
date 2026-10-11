from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from newsr.domain import AppOptions, ArticleContent, ViewMode
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import article_pane, body_source, header_text, url_source


def test_ui_loads_articles_in_insertion_order_and_shows_position(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    appended_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Appended title",
        author="Reporter",
        published_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        body="Appended source text",
    )
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Older summary", "done")
    app.storage.upsert_article_source(appended_article)
    app.storage.update_translation(appended_article.article_id, "Appended translated title", "Appended text", "done")
    app.storage.update_summary(appended_article.article_id, "Appended summary", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id
            body = body_source(app)
            assert "Article # 1 of 2" in header_text(app)
            assert "Title: Older translated title" in header_text(app)
            assert "Older text" in body
            assert url_source(app) == f"URL: {article_content.url}"

            await pilot.press("right")

            body = body_source(app)
            assert app.current_article is not None
            assert app.current_article.article_id == appended_article.article_id
            assert "Article # 2 of 2" in header_text(app)
            assert "Title: Appended translated title" in header_text(app)
            assert "Appended text" in body
            assert url_source(app) == f"URL: {appended_article.url}"

    asyncio.run(runner())


def test_ui_reader_navigation_still_works_after_command_palette(app_config, tmp_path, article_content) -> None:
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
            await pilot.press("ctrl+p", "escape")
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


def test_ui_restores_last_read_article_on_restart(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    appended_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Appended title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Appended source text",
    )
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Older summary", "done")
    app.storage.upsert_article_source(appended_article)
    app.storage.update_translation(
        appended_article.article_id, "Appended translated title", "Appended text", "done"
    )
    app.storage.update_summary(appended_article.article_id, "Appended summary", "done")

    async def first_run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("right")
            assert app.current_article is not None
            assert app.current_article.article_id == appended_article.article_id

    asyncio.run(first_run())

    restarted = NewsReaderApp(app_config, storage_path)

    async def second_run() -> None:
        async with restarted.run_test() as pilot:
            await pilot.pause()
            assert restarted.current_article is not None
            assert restarted.current_article.article_id == appended_article.article_id
            assert "Article # 2 of 2" in header_text(restarted)

    asyncio.run(second_run())


def test_ui_falls_back_when_last_read_article_is_missing(app_config, tmp_path, article_content) -> None:
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
    app.storage.update_summary(article_content.article_id, "Older summary", "done")
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")
    app.storage.update_summary(newer_article.article_id, "Newer summary", "done")
    app.storage.save_reader_state(
        "[ALL]",
        app.reader_state.__class__(
            article_id=newer_article.article_id,
            view_mode=ViewMode.FULL,
            scroll_offset=7,
        )
    )
    app.storage.connection.execute("DELETE FROM articles WHERE article_id = ?", (newer_article.article_id,))
    app.storage.connection.execute("DELETE FROM jobs WHERE article_id = ?", (newer_article.article_id,))
    app.storage.connection.commit()
    app.storage.close()

    restarted = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with restarted.run_test() as pilot:
            await pilot.pause()
            assert restarted.current_article is not None
            assert restarted.current_article.article_id == article_content.article_id
            assert restarted.reader_state.article_id == article_content.article_id
            assert "Article # 1 of 1" in header_text(restarted)

    asyncio.run(runner())


def test_ui_restores_last_read_article_on_restart_with_saved_theme(
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
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")
    app.storage.update_summary(newer_article.article_id, "Newer summary", "done")
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Older summary", "done")
    app.storage.save_reader_state(
        "[ALL]",
        app.reader_state.__class__(
            article_id=newer_article.article_id,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        )
    )
    app.storage.save_options(AppOptions(theme_name="old fido"))
    app.storage.close()

    restarted = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with restarted.run_test() as pilot:
            await pilot.pause()
            assert restarted.theme == "old fido"
            assert restarted.current_article is not None
            assert restarted.current_article.article_id == newer_article.article_id
            state = restarted.storage.load_reader_state("[ALL]")
            assert state.article_id == newer_article.article_id

    asyncio.run(runner())
