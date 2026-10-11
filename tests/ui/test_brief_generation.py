from __future__ import annotations

import asyncio
from threading import Event

import pytest

from newsr.brief import BriefPeriod
from newsr.cancellation import RefreshCancellation
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
from tests.ui.support.fakes import FakeBriefLLM
from tests.ui.support.screens import (
    brief_body,
    brief_reader_body,
    brief_reader_pane,
    brief_reader_screen,
    brief_screen,
)


class PausingFinalRepairBriefLLM(FakeBriefLLM):
    def __init__(self) -> None:
        super().__init__("# Brief\n\nFixed report [1]")
        self.repair_started = Event()
        self.release_repair = Event()

    def synthesize_brief_report(
        self,
        system_prompt: str,
        notes: str,
        *,
        max_tokens: int,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.report_calls.append((system_prompt, notes, max_tokens))
        if len(self.report_calls) == 1:
            return "# Brief\n\nBad report [99]"
        self.repair_started.set()
        self.release_repair.wait(timeout=5)
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        return self.report


class BlockingBriefLLM(FakeBriefLLM):
    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.cancelled = Event()

    def shorten_brief_notes(
        self,
        system_prompt: str,
        notes: str,
        *,
        max_tokens: int,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        assert cancellation is not None
        self.started.set()
        cancellation.cancelled_event.wait(timeout=5)
        if cancellation.is_cancelled:
            self.cancelled.set()
        cancellation.raise_if_cancelled()
        return "unused"


@pytest.mark.provider_home
def test_ui_brief_generate_shows_report_and_marks_provider_read(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.llm_client = FakeBriefLLM("# Brief\n\nGenerated provider report [1]")  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-1",
        title="Brief item",
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
            screen.period = BriefPeriod.ALL_UNREAD
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                reader = brief_reader_screen(app)
                if reader is not None and "Generated provider report" in brief_reader_body(app):
                    break
            else:
                raise AssertionError("brief report was not rendered")

            assert "## Statistics" in brief_reader_body(app)
            assert "BBC News: 1" in brief_reader_body(app)
            assert brief_screen(app) is None
            assert brief_reader_screen(app) is not None
            assert app.storage.load_reader_state("bbc").article_id == "bbc:brief-1"
            assert app.storage.load_reader_state("[ALL]").article_id is None

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_generate_shows_repair_progress_step(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    llm = PausingFinalRepairBriefLLM()
    app.llm_client = llm  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-repair-progress",
        title="Brief repair progress",
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
            screen.period = BriefPeriod.ALL_UNREAD
            app.generate_brief()
            for _ in range(30):
                await pilot.pause()
                if "repairing final brief, attempt 1 of 5" in brief_body(app):
                    break
            else:
                raise AssertionError("brief repair progress was not rendered")

            assert llm.repair_started.is_set()
            llm.release_repair.set()
            for _ in range(30):
                await pilot.pause()
                if brief_reader_screen(app) is not None and "Fixed report [1]" in brief_reader_body(app):
                    break
            else:
                raise AssertionError("brief reader was not opened after repair")

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_generate_localizes_repair_progress_step_in_russian(app_config, tmp_path) -> None:
    app_config.ui.locale = "ru"
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    llm = PausingFinalRepairBriefLLM()
    app.llm_client = llm  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-repair-progress-ru",
        title="Brief repair progress ru",
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
            screen.period = BriefPeriod.ALL_UNREAD
            app.generate_brief()
            for _ in range(30):
                await pilot.pause()
                body = brief_body(app)
                if "исправление итогового обзора, попытка 1 из 5" in body:
                    break
            else:
                raise AssertionError("localized brief repair progress was not rendered")

            assert "repairing final brief, attempt 1 of 5" not in brief_body(app)
            assert llm.repair_started.is_set()
            llm.release_repair.set()
            for _ in range(30):
                await pilot.pause()
                if brief_reader_screen(app) is not None and "Fixed report [1]" in brief_reader_body(app):
                    break
            else:
                raise AssertionError("brief reader was not opened after repair")

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_reader_escape_returns_to_provider_home(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.llm_client = FakeBriefLLM("# Brief\n\nGenerated provider report [1]")  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-reader-close",
        title="Brief reader close",
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
            screen.period = BriefPeriod.ALL_UNREAD
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                if brief_reader_screen(app) is not None:
                    break
            else:
                raise AssertionError("brief reader was not opened")

            await pilot.press("escape")
            await pilot.pause()

            assert brief_reader_screen(app) is None
            assert brief_screen(app) is None
            assert app.provider_home_open is True
            assert getattr(app.focused, "id", None) == "provider-home-table"

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_reader_up_down_scroll_report(app_config, tmp_path) -> None:
    report = "# Brief\n\n" + "\n\n".join(f"Paragraph {index} [1]" for index in range(80))
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.llm_client = FakeBriefLLM(report)  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-reader-scroll",
        title="Brief reader scroll",
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
            screen.period = BriefPeriod.ALL_UNREAD
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                if brief_reader_screen(app) is not None:
                    break
            else:
                raise AssertionError("brief reader was not opened")

            pane = brief_reader_pane(app)
            assert pane.scroll_y == 0

            await pilot.press("down")
            await pilot.pause()
            assert pane.scroll_y > 0

            await pilot.press("up")
            await pilot.pause()
            assert pane.scroll_y == 0

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_escape_cancels_generation(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    llm = BlockingBriefLLM()
    app.llm_client = llm  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-cancel",
        title="Brief cancel",
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
            screen.period = BriefPeriod.ALL_UNREAD
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                if llm.started.is_set():
                    break
            assert llm.started.is_set()
            await pilot.press("escape")
            for _ in range(20):
                await pilot.pause()
                if llm.cancelled.is_set():
                    break
            assert llm.cancelled.is_set()
            assert "Generation was cancelled" in brief_body(app)
            assert app.storage.load_reader_state("bbc").article_id is None

    asyncio.run(runner())
