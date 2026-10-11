from __future__ import annotations

import asyncio
from threading import Event

from textual.widgets import Static

from newsr.cancellation import RefreshCancellation
from newsr.ui import NewsReaderApp

from tests.ui.support.screens import confirm_dialog_screen


def confirm_dialog_body(app: NewsReaderApp) -> str:
    screen = confirm_dialog_screen(app)
    assert screen is not None
    return str(screen.query_one("#confirm-dialog-body", Static).content)


def confirm_dialog_focused_button_id(app: NewsReaderApp) -> str | None:
    focused = app.focused
    return getattr(focused, "id", None)


class SequenceResponsiveLLM:
    def __init__(self, responses: list[Exception | None]) -> None:
        self.responses = responses
        self.calls = 0

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        response = self.responses[index]
        if response is not None:
            raise response


class BlockingResponsiveLLM:
    def __init__(self) -> None:
        self.calls = 0
        self.started = Event()
        self.release = Event()

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        assert cancellation is not None
        self.calls += 1
        self.started.set()
        while not self.release.wait(timeout=0.05):
            cancellation.raise_if_cancelled()
        cancellation.raise_if_cancelled()


def skip_first_refresh_start(app: NewsReaderApp) -> None:
    original_start = app._refresh.start
    skipped = False

    def start_once(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        nonlocal skipped
        if not skipped:
            skipped = True
            return
        original_start(*args, **kwargs)

    app._refresh.start = start_once  # type: ignore[method-assign]


def test_ui_startup_refresh_retries_llm_preflight_before_launching_refresh(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.llm_client = SequenceResponsiveLLM([RuntimeError("synthetic timeout"), None])  # type: ignore[assignment]

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._refresh._run)
        return object()

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            for _ in range(20):
                await pilot.pause()
                if confirm_dialog_screen(app) is not None:
                    break
            assert confirm_dialog_body(app) == "LLM is not responsive: synthetic timeout. Try again?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if calls:
                    break
            assert calls == [app._refresh._run]
            assert app.llm_client.calls == 2  # type: ignore[union-attr]
            assert app.refresh_in_progress is True

    asyncio.run(runner())


def test_ui_confirm_dialog_supports_tab_and_arrow_navigation(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    skip_first_refresh_start(app)
    app.llm_client = SequenceResponsiveLLM([RuntimeError("synthetic timeout"), RuntimeError("synthetic timeout")])  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("d")
            for _ in range(20):
                await pilot.pause()
                if confirm_dialog_screen(app) is not None:
                    break

            assert confirm_dialog_focused_button_id(app) == "confirm-dialog-confirm"

            await pilot.press("tab")
            await pilot.pause()
            assert confirm_dialog_focused_button_id(app) == "confirm-dialog-cancel"

            await pilot.press("left")
            await pilot.pause()
            assert confirm_dialog_focused_button_id(app) == "confirm-dialog-confirm"

            await pilot.press("right")
            await pilot.pause()
            assert confirm_dialog_focused_button_id(app) == "confirm-dialog-cancel"

            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if confirm_dialog_screen(app) is None:
                    break

            assert confirm_dialog_screen(app) is None
            assert app.refresh_in_progress is False
            assert app.status_text == "ready"

    asyncio.run(runner())


def test_ui_canceling_llm_preflight_stops_manual_refresh(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    skip_first_refresh_start(app)
    app.llm_client = SequenceResponsiveLLM([RuntimeError("synthetic timeout")])  # type: ignore[assignment]

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._refresh._run)
        return object()

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("d")
            for _ in range(20):
                await pilot.pause()
                if confirm_dialog_screen(app) is not None:
                    break
            assert confirm_dialog_body(app) == "LLM is not responsive: synthetic timeout. Try again?"
            await pilot.press("escape")
            for _ in range(20):
                await pilot.pause()
                if confirm_dialog_screen(app) is None:
                    break
            assert confirm_dialog_screen(app) is None
            assert calls == []
            assert app.refresh_in_progress is False
            assert app.status_text == "ready"

    asyncio.run(runner())


def test_ui_ignores_duplicate_download_while_llm_preflight_is_running(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    skip_first_refresh_start(app)
    app.llm_client = BlockingResponsiveLLM()  # type: ignore[assignment]

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._refresh._run)
        return object()

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("d")
            for _ in range(20):
                await pilot.pause()
                if app.llm_client.started.is_set():  # type: ignore[union-attr]
                    break
            assert app.llm_client.started.is_set()  # type: ignore[union-attr]
            await pilot.press("d")
            await pilot.pause()
            assert app.llm_client.calls == 1  # type: ignore[union-attr]
            app.llm_client.release.set()  # type: ignore[union-attr]
            for _ in range(20):
                await pilot.pause()
                if calls:
                    break
            assert calls == [app._refresh._run]
            assert app.refresh_in_progress is True

    asyncio.run(runner())
