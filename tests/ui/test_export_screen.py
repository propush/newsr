from __future__ import annotations

import asyncio

from textual.widgets import Static

from newsr.domain import ViewMode
from newsr.export import ExportAction, ExportResult
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.fakes import FakeExportService
from tests.ui.support.screens import export_screen


def test_ui_pressing_e_without_current_article_sets_status(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is None
            assert app.query_one("#status", Static).content == "no article to export"

    asyncio.run(runner())


def test_ui_pressing_e_opens_export_screen(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            screen = export_screen(app)
            assert screen is not None
            assert "Title: Translated title" in screen.query_one("#export-body", Static).content
            assert "Mode: full" in screen.query_one("#export-body", Static).content

    asyncio.run(runner())


def test_ui_pressing_e_opens_export_screen_for_original_mode(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("s", "s", "e")
            await pilot.pause()
            screen = export_screen(app)
            assert screen is not None
            export_body = screen.query_one("#export-body", Static).content
            assert "Title: Example title" in export_body
            assert "Mode: original" in export_body

    asyncio.run(runner())


def test_ui_export_screen_runs_action_and_closes_on_success(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    fake_export = FakeExportService()
    app.export_service = fake_export

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("s")
            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is not None

            await pilot.press("2")
            await pilot.pause()

            assert fake_export.calls == [(ExportAction.COPY_PNG, article_content.article_id, ViewMode.SUMMARY, app.theme)]
            assert export_screen(app) is None
            assert app.query_one("#status", Static).content == "saved png export to exports/test.png"

    asyncio.run(runner())


def test_ui_export_screen_arrow_keys_move_focus_and_activate_selection(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    fake_export = FakeExportService()
    app.export_service = fake_export

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is not None
            assert getattr(app.focused, "id", None) == "export-save-png"

            await pilot.press("right")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "export-copy-png"

            await pilot.press("down")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "export-copy-markdown"

            await pilot.press("down")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "export-cancel"

            await pilot.press("up")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "export-copy-markdown"

            await pilot.press("enter")
            await pilot.pause()

            assert fake_export.calls == [(ExportAction.COPY_MARKDOWN, article_content.article_id, ViewMode.FULL, app.theme)]
            assert export_screen(app) is None

    asyncio.run(runner())


def test_ui_export_screen_stays_open_on_failure(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.export_service = FakeExportService(ExportResult(False, "clipboard image export is not supported"))

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is not None

            await pilot.press("2")
            await pilot.pause()

            assert export_screen(app) is not None
            assert app.query_one("#status", Static).content == "clipboard image export is not supported"

    asyncio.run(runner())
