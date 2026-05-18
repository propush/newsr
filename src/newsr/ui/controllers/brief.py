from __future__ import annotations

from threading import Thread
from typing import TYPE_CHECKING

from textual.app import ScreenStackError

from ...brief import BriefOptions, BriefProgress, BriefService
from ...cancellation import RefreshCancellation, RefreshCancelled
from ..screens import BriefReaderScreen, BriefScreen

if TYPE_CHECKING:
    from ..app import NewsReaderApp


class BriefController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._screen: BriefScreen | None = None
        self._reader_screen: BriefReaderScreen | None = None
        self._thread: Thread | None = None
        self._cancellation: RefreshCancellation | None = None

    def show(self) -> None:
        if not self._app.provider_home_open:
            return
        if self._screen is not None:
            return
        if self._reader_screen is not None:
            return
        screen = BriefScreen(self._app.ui)
        self._screen = screen
        self._app.push_screen(screen)

    def generate(self) -> None:
        screen = self._screen
        if screen is None or self._cancellation is not None:
            return
        options = screen.current_options()
        screen.set_generating(True)
        screen.set_content(self._app.ui.text("brief.body.starting"))
        cancellation = RefreshCancellation()
        self._cancellation = cancellation
        self._thread = Thread(
            target=self._run_generate,
            args=(options, cancellation),
            name="newsr-brief",
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        if self._cancellation is not None:
            self.cancel()
            if self._screen is not None:
                self._screen.set_generating(False)
                self._screen.set_content(self._app.ui.text("brief.body.cancelled"))
            return
        self._dismiss_screen()
        self._dismiss_reader_screen()

    def close_reader(self) -> None:
        self._dismiss_reader_screen()

    def cancel(self) -> None:
        cancellation = self._cancellation
        self._cancellation = None
        self._thread = None
        if cancellation is not None:
            cancellation.cancel()

    def _run_generate(self, options: BriefOptions, cancellation: RefreshCancellation) -> None:
        service = BriefService(self._app.config, self._app.storage, self._app.llm_client)
        try:
            result = service.generate(
                options,
                cancellation=cancellation,
                on_progress=lambda progress: self._schedule_progress(cancellation, progress),
            )
        except RefreshCancelled:
            return
        except Exception as exc:
            if self._app.is_mounted:
                self._app.call_from_thread(self._finish_error, cancellation, str(exc))
            return
        if self._app.is_mounted:
            self._app.call_from_thread(self._finish_success, cancellation, result.report)

    def _finish_success(self, cancellation: RefreshCancellation, report: str) -> None:
        if cancellation is not self._cancellation:
            return
        self._thread = None
        self._cancellation = None
        if self._screen is not None:
            self._screen.set_generating(False)
        self._dismiss_screen(restore_focus=False)
        self._show_reader(report)
        self._app._provider_home.refresh_rows()
        self._app.refresh_view()

    def _finish_error(self, cancellation: RefreshCancellation, error_text: str) -> None:
        if cancellation is not self._cancellation:
            return
        self._thread = None
        self._cancellation = None
        if self._screen is not None:
            self._screen.set_error(error_text)

    def _schedule_progress(self, cancellation: RefreshCancellation, progress: BriefProgress) -> None:
        if self._app.is_mounted:
            self._app.call_from_thread(self._handle_progress, cancellation, progress)

    def _handle_progress(self, cancellation: RefreshCancellation, progress: BriefProgress) -> None:
        if cancellation is not self._cancellation or self._screen is None:
            return
        self._screen.set_progress(progress)

    def _show_reader(self, report: str) -> None:
        if self._reader_screen is not None:
            return
        screen = BriefReaderScreen(self._app.ui, report)
        self._reader_screen = screen
        self._app.push_screen(screen)

    def _dismiss_screen(self, *, restore_focus: bool = True) -> None:
        screen = self._screen
        self._screen = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass
        if restore_focus:
            self._app.restore_navigation_focus()

    def _dismiss_reader_screen(self) -> None:
        screen = self._reader_screen
        self._reader_screen = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass
        self._app.restore_navigation_focus()
