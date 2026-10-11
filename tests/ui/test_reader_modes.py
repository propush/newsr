from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from newsr.domain import ArticleContent, ViewMode
from newsr.ui import NewsReaderApp

from tests.ui.support.reader import (
    article_pane,
    body_source,
    footer_bindings,
    header_text,
    url_source,
)


def test_ui_cycles_between_full_and_original_without_summary(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            assert app.reader_state.view_mode == ViewMode.ORIGINAL
            assert "Title: Example title" in header_text(app)
            assert body_source(app) == "Paragraph one.\n\nParagraph two."
            await pilot.press("s")
            assert app.reader_state.view_mode == ViewMode.FULL
            assert "Title: Translated title" in header_text(app)
            assert body_source(app) == "Translated text"

    asyncio.run(runner())


def test_ui_arrow_scroll_actions_do_not_raise(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(80))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", tall_body, "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("down", "up")
            assert app.query_one("#article-pane").scroll_target_y >= 0

    asyncio.run(runner())


def test_ui_space_pagedown_and_b_pageup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(200))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", tall_body, "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            pane = app.query_one("#article-pane")
            assert pane.scroll_target_y == 0

            await pilot.press("space")
            await pilot.pause()
            after_page_down = pane.scroll_target_y
            assert after_page_down > 0

            await pilot.press("b")
            await pilot.pause()
            assert pane.scroll_target_y < after_page_down

    asyncio.run(runner())


def test_ui_reader_footer_hides_pgup_and_pgdn(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            bindings = footer_bindings(app)
            actions = {action for _, _, action in bindings}

            assert "page_up" not in actions
            assert "page_down" not in actions
            assert "classify_article_categories" in actions
            assert "cycle_view_mode" in actions
            assert "show_or_refresh_more_info" in actions

    asyncio.run(runner())


def test_ui_space_advances_to_next_article_at_bottom(app_config, tmp_path, article_content) -> None:
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
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(200))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Older translated title", tall_body, "done")
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            pane = app.query_one("#article-pane")
            pane.scroll_to(y=pane.max_scroll_y, animate=False)
            await pilot.pause()
            await pilot.press("space")
            await pilot.pause()

            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id
            assert body_source(app) == "Newer text"

    asyncio.run(runner())


def test_ui_hides_space_hints_from_footer(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    bindings = {binding.key: binding for _key, binding in app._bindings}

    assert bindings["left"].show is False
    assert bindings["right"].show is False
    assert bindings["up"].show is False
    assert bindings["down"].show is False
    assert bindings["space"].show is False
    assert bindings["b"].show is False


def test_ui_mode_cycle_shows_full_summary_original_and_full(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header_before = header_text(app)
            body_before = body_source(app)
            url_before = url_source(app)
            await pilot.press("s")
            header_after = header_text(app)
            body_after = body_source(app)
            url_after = url_source(app)
            assert "Title: Translated title" in header_before
            assert "Title: Translated title" in header_after
            assert "Mode : full" in header_before
            assert "Mode : summary" in header_after
            assert body_before == "Translated text"
            assert body_after == "Summary text"
            assert url_before == f"URL: {article_content.url}"
            assert url_after == f"URL: {article_content.url}"
            await pilot.press("s")
            assert app.reader_state.view_mode == ViewMode.ORIGINAL
            assert "Title: Example title" in header_text(app)
            assert "Mode : original" in header_text(app)
            assert body_source(app) == "Paragraph one.\n\nParagraph two."
            assert url_source(app) == f"URL: {article_content.url}"
            await pilot.press("s")
            assert app.reader_state.view_mode == ViewMode.FULL
            assert "Title: Translated title" in header_text(app)
            assert "Mode : full" in header_text(app)
            assert body_source(app) == "Translated text"

    asyncio.run(runner())


def test_ui_mode_change_resets_scroll_and_persists_zero_offset(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id,
        "Translated title",
        "\n\n".join(f"Translated paragraph {index}" for index in range(140)),
        "done",
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            pane = article_pane(app)
            assert pane.max_scroll_y >= 20
            pane.scroll_to(y=20, animate=False)
            await pilot.pause()
            assert int(pane.scroll_y) == 20

            await pilot.press("s")
            await pilot.pause()

            assert app.reader_state.view_mode == ViewMode.SUMMARY
            assert int(article_pane(app).scroll_y) == 0
            assert app.reader_state.scroll_offset == 0
            assert app.storage.load_reader_state("[ALL]").scroll_offset == 0
            assert app.storage.load_reader_state("[ALL]").view_mode == ViewMode.SUMMARY

    asyncio.run(runner())
