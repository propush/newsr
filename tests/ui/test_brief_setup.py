from __future__ import annotations

import asyncio
from threading import Thread

import pytest
from textual.widgets import Button, Checkbox, RadioButton, RadioSet

from newsr.brief import BriefPeriod
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
from tests.ui.support.fakes import FakeBriefLLM
from tests.ui.support.screens import brief_body, brief_reader_screen, brief_screen


@pytest.mark.provider_home
def test_ui_provider_home_b_opens_brief_screen_with_defaults(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            screen = brief_screen(app)
            assert screen is not None
            options = screen.current_options()
            assert options.period == "last_24h"
            assert options.only_unread is True
            assert options.include_topics is False
            assert options.mark_read is True

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_setup_tab_moves_between_control_groups(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            assert brief_screen(app) is not None
            assert getattr(app.focused, "id", None) == "brief-period"

            await pilot.press("tab")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "brief-only-unread"

            await pilot.press("tab")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "brief-include-topics"

            await pilot.press("tab")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "brief-mark-read"

            await pilot.press("shift+tab")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "brief-include-topics"

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_unread_toggle_is_implied_for_all_unread(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            screen = brief_screen(app)
            assert screen is not None
            checkbox = screen.query_one("#brief-only-unread", Checkbox)
            assert checkbox.value is True
            assert checkbox.disabled is False

            await pilot.press("tab", "space")
            await pilot.pause()
            assert screen.current_options().only_unread is False

            screen.query_one("#brief-period-unread", RadioButton).value = True
            await pilot.pause()
            assert screen.current_options().period == BriefPeriod.ALL_UNREAD
            assert screen.current_options().only_unread is True
            assert checkbox.value is True
            assert checkbox.disabled is True

            screen.query_one("#brief-period", RadioSet).focus()
            await pilot.press("tab")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "brief-include-topics"

            screen.set_generating(True)
            screen.set_generating(False)
            assert checkbox.disabled is True

            screen.query_one("#brief-period-week", RadioButton).value = True
            await pilot.pause()
            assert screen.current_options().period == BriefPeriod.LAST_WEEK
            assert screen.current_options().only_unread is False
            assert checkbox.value is False
            assert checkbox.disabled is False

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_b_does_not_open_brief_during_refresh_preflight(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            app._refresh._preflight_thread = Thread(name="test-refresh-preflight")
            await pilot.press("b")
            await pilot.pause()

            assert brief_screen(app) is None
            assert app.status_text == "Brief review is unavailable while refresh is running."

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_generate_does_not_start_when_refresh_becomes_busy(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    llm = FakeBriefLLM("# Brief\n\nGenerated provider report")
    app.llm_client = llm  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-refresh-busy",
        title="Brief refresh busy",
        body="Translated body",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            screen = brief_screen(app)
            assert screen is not None

            app.refresh_in_progress = True
            app.generate_brief()
            await pilot.pause()

            assert brief_screen(app) is screen
            assert brief_reader_screen(app) is None
            assert "Brief review is unavailable while refresh is running." in brief_body(app)
            assert screen.generating is False
            assert screen.query_one("#brief-generate", Button).disabled is False
            assert llm.shorten_calls == []
            assert llm.report_calls == []
            assert app.storage.load_reader_state("bbc").article_id is None

    asyncio.run(runner())
