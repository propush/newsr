from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from textual.widgets import Input, Static

from newsr.ui import NewsReaderApp, TextInputDialogScreen

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import body_source, header_text
from tests.ui.support.screens import confirm_dialog_screen
from tests.ui.support.source_manager import (
    category_screen,
    provider_list,
    provider_row_index,
    target_list,
    wait_for_source_manager,
)


def text_input_dialog_screen(app: NewsReaderApp) -> TextInputDialogScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, TextInputDialogScreen):
            return screen
    return None


def test_ui_source_manager_save_persists_selection_without_starting_refresh(app_config, tmp_path) -> None:
    launch_calls: list[object] = []
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    original_start_refresh = app._refresh.start
    disable_startup_refresh(app)

    def fake_launch_refresh_thread() -> object:
        launch_calls.append(object())
        return launch_calls[-1]

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            assert screen is not None
            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()
            app._refresh.start = original_start_refresh  # type: ignore[method-assign]
            screen.action_toggle_item()
            screen.action_save_selection()
            await pilot.pause()
            assert category_screen(app) is None
            assert len(launch_calls) == 0
            assert app.status_text == "sources saved"
            providers = app.storage.list_providers()
            assert any(provider.provider_id == "bbc" and provider.enabled is False for provider in providers)

    asyncio.run(runner())


def test_ui_source_manager_save_defers_when_refresh_running(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.refresh_in_progress = True
    launch_calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        launch_calls.append(object())
        return launch_calls[-1]

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            initial_header = header_text(app)
            initial_body = body_source(app)
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()
            await pilot.press("tab", "space")
            await pilot.press("a")
            await pilot.pause()
            assert [target.target_key for target in app.storage.list_selected_targets("bbc")] == [
                "technology",
                "business",
                "entertainment_and_arts",
            ]
            assert app.status_text == "sources saved"
            assert len(launch_calls) == 0
            assert header_text(app) == initial_header
            assert body_source(app) == initial_body

    asyncio.run(runner())


def test_ui_source_manager_enable_provider_starts_due_refresh_after_current_refresh(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.mark_refresh_completed("bbc")
    app.refresh_in_progress = True
    calls: list[tuple[list[str] | None, bool]] = []
    app._refresh.start = lambda provider_ids=None, *, force=False: calls.append((provider_ids, force))  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            provider_list(app).move_cursor(row=provider_row_index(app, "TechCrunch"), column=0, animate=False)
            await pilot.pause()
            await pilot.press("space")
            await pilot.press("a")
            await pilot.pause()
            assert app.storage.get_provider("techcrunch").enabled is True
            assert calls == []

            app._refresh._processed_provider_count = 1
            app._refresh._finish()
            await pilot.pause()

            assert calls == [(["techcrunch"], False)]

    asyncio.run(runner())


def test_ui_source_manager_schedule_change_starts_due_refresh_after_current_refresh(
    app_config, tmp_path
) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    app.storage.mark_refresh_completed("bbc")
    app.storage.mark_refresh_completed("techcrunch")
    app.storage.connection.execute(
        """
        UPDATE providers
        SET last_refresh_completed_at = ?
        WHERE provider_id = ?
        """,
        ((datetime.now(UTC) - timedelta(minutes=2)).isoformat(), "techcrunch"),
    )
    app.storage.connection.commit()
    app.refresh_in_progress = True
    calls: list[tuple[list[str] | None, bool]] = []
    app._refresh.start = lambda provider_ids=None, *, force=False: calls.append((provider_ids, force))  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            provider_list(app).move_cursor(row=provider_row_index(app, "TechCrunch"), column=0, animate=False)
            await pilot.pause()
            await pilot.press("u")
            await pilot.pause()

            screen = text_input_dialog_screen(app)
            assert screen is not None
            screen.query_one("#text-input-dialog-input", Input).value = "*/1 * * * *"
            await pilot.press("enter")
            await pilot.pause()

            assert app.storage.get_provider("techcrunch").update_schedule == "*/1 * * * *"
            assert calls == []

            app._refresh._processed_provider_count = 1
            app._refresh._finish()
            await pilot.pause()

            assert calls == [(["techcrunch"], False)]

    asyncio.run(runner())


def test_ui_source_manager_schedule_dialog_shows_configured_default_schedule(app_config, tmp_path) -> None:
    app_config.articles.update_schedule = "*/15 * * * *"
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and provider_list(app).row_count and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()
            await pilot.press("u")
            await pilot.pause()
            screen = text_input_dialog_screen(app)
            assert screen is not None
            assert str(screen.query_one("#text-input-dialog-body", Static).content) == (
                "Enter a 5-field cron expression. Leave it blank to use the global default schedule: "
                "*/15 * * * *."
            )
            assert screen.query_one("#text-input-dialog-input", Input).placeholder == (
                "Leave blank for */15 * * * *"
            )

    asyncio.run(runner())


def test_ui_source_manager_navigation_still_works_after_schedule_dialog_cancel(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("c")
            await wait_for_source_manager(app, pilot)
            table = provider_list(app)
            bbc_row = provider_row_index(app, "BBC News")
            table.move_cursor(row=bbc_row, column=0, animate=False)
            await pilot.pause()

            await pilot.press("u", "escape")
            await pilot.pause()
            await pilot.press("down")
            await pilot.pause()

            assert text_input_dialog_screen(app) is None
            assert table.has_focus
            assert table.cursor_row != bbc_row

    asyncio.run(runner())


def test_ui_source_manager_navigation_still_works_after_delete_dialog_cancel(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )
    app.rebuild_provider_registry()

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("c")
            await wait_for_source_manager(app, pilot)
            table = provider_list(app)
            topic_row = provider_row_index(app, "OpenAI policy")
            table.move_cursor(row=topic_row, column=0, animate=False)
            await pilot.pause()

            await pilot.press("x", "escape")
            await pilot.pause()

            assert confirm_dialog_screen(app) is None
            assert table.has_focus
            assert table.cursor_row == topic_row

    asyncio.run(runner())
