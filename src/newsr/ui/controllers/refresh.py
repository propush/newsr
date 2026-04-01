from __future__ import annotations

from threading import Event, Thread
from time import monotonic
from typing import TYPE_CHECKING

from ...cancellation import RefreshCancellation, RefreshCancelled
from ..screens import ConfirmDialogScreen

if TYPE_CHECKING:
    from ..app import NewsReaderApp


class RefreshController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self.in_progress = False
        self._thread: Thread | None = None
        self._preflight_thread: Thread | None = None
        self._cancellation: RefreshCancellation | None = None
        self._confirm_screen: ConfirmDialogScreen | None = None
        self._auto_select_first_ready_article = False
        self.status_text: str = app.ui.text("app.status.ready")
        self._status_busy = False
        self._status_override_until = 0.0

    @property
    def status_busy(self) -> bool:
        return self._status_busy

    def start(self) -> None:
        if self.in_progress or self._preflight_thread is not None or self._app._shutdown_requested:
            return
        self._app._navigation._auto_fetch_armed = False
        self._auto_select_first_ready_article = not self._app.articles
        self._cancellation = RefreshCancellation()
        self.set_status_text(self._app.ui.text("app.status.checking_llm"), busy=True)
        self._app.refresh_view()
        self._preflight_thread = self._launch_preflight_thread()

    def _launch_preflight_thread(self) -> Thread:
        thread = Thread(target=self._run_preflight, name="newsr-llm-preflight", daemon=True)
        thread.start()
        return thread

    def _run_preflight(self) -> None:
        cancellation = self._cancellation
        try:
            if cancellation is None:
                return
            while not self._app._shutdown_requested:
                try:
                    cancellation.raise_if_cancelled()
                    self._app.llm_client.check_responsive(cancellation)
                except RefreshCancelled:
                    return
                except Exception as exc:
                    if not self._prompt_retry(str(exc), cancellation):
                        self._call_from_thread_if_ready(self._abort_preflight)
                        return
                    self._call_from_thread_if_ready(self._set_preflight_status, True)
                    continue
                self._call_from_thread_if_ready(self._start_refresh_after_preflight)
                return
        finally:
            self._call_from_thread_if_ready(self._clear_preflight_thread)

    def _launch_thread(self) -> Thread:
        thread = Thread(target=self._run, name="newsr-refresh", daemon=True)
        thread.start()
        return thread

    def _start_refresh_after_preflight(self) -> None:
        cancellation = self._cancellation
        if cancellation is None or self._app._shutdown_requested or cancellation.is_cancelled:
            self._abort_preflight()
            return
        self.set_status_text(self._app.ui.text("app.status.ready"), busy=False)
        self.in_progress = True
        self._thread = self._launch_thread()
        self._app.refresh_view()

    def _set_preflight_status(self, busy: bool) -> None:
        self.set_status_text(self._app.ui.text("app.status.checking_llm"), busy=busy)
        self._app.refresh_view()

    def _abort_preflight(self) -> None:
        if self.in_progress:
            return
        if not self._app._shutdown_requested:
            self.set_status_text(self._app.ui.text("app.status.ready"), busy=False)
            self._app.refresh_view()
        self._cancellation = None

    def _clear_preflight_thread(self) -> None:
        self._preflight_thread = None

    def _prompt_retry(self, error: str, cancellation: RefreshCancellation) -> bool:
        decision = Event()
        accepted = False

        def resolve(result: bool | None) -> None:
            nonlocal accepted
            self._confirm_screen = None
            accepted = bool(result)
            decision.set()

        def show_dialog() -> None:
            if self._app._shutdown_requested or cancellation.is_cancelled:
                decision.set()
                return
            self._set_preflight_status(False)
            screen = ConfirmDialogScreen(
                self._app.ui,
                title=self._app.ui.text("confirm_dialog.llm_unresponsive.header"),
                body=self._app.ui.text("confirm_dialog.llm_unresponsive.body", error=error),
                confirm_label=self._app.ui.text("confirm_dialog.button.retry"),
                cancel_label=self._app.ui.text("confirm_dialog.button.cancel"),
            )
            self._confirm_screen = screen
            self._app.push_screen(screen, callback=resolve)

        if not self._call_from_thread_if_ready(show_dialog):
            return False
        while not decision.wait(0.1):
            if self._app._shutdown_requested or cancellation.is_cancelled:
                self._call_from_thread_if_ready(self._dismiss_confirm_screen, False)
                return False
        return accepted

    def _dismiss_confirm_screen(self, result: bool) -> None:
        screen = self._confirm_screen
        if screen is None:
            return
        try:
            screen.dismiss(result)
        except Exception:
            self._confirm_screen = None

    def _run(self) -> None:
        try:
            self._app.pipeline.refresh(
                self.set_status,
                self._handle_article_ready,
                self._cancellation,
            )
        finally:
            self._call_from_thread_if_ready(self._finish)

    def _finish(self) -> None:
        self.in_progress = False
        self._status_busy = False
        if not self._app._shutdown_requested:
            self._app.load_articles()
            if self._app.provider_home_open:
                self._app._provider_home.refresh_rows()
        self._thread = None
        self._cancellation = None

    def _handle_article_ready(self, article_id: str) -> None:
        self._call_from_thread_if_ready(self._load_ready_article, article_id)

    def _call_from_thread_if_ready(self, callback, *args) -> bool:  # type: ignore[no-untyped-def]
        if not self._app.is_mounted:
            return False
        loop = getattr(self._app, "_loop", None)
        if loop is None or loop.is_closed():
            return False
        try:
            self._app.call_from_thread(callback, *args)
        except RuntimeError:
            return False
        return True

    def _load_ready_article(self, article_id: str) -> None:
        auto_select_first = self._auto_select_first_ready_article and not self._app.articles
        self._app.load_articles(auto_select_first=auto_select_first)
        if self._app.provider_home_open:
            self._app._provider_home.refresh_rows()
        if auto_select_first and self._app.articles:
            self._auto_select_first_ready_article = False

    def set_status(self, value: str) -> None:
        localized_value = self._app.ui.status(value)
        if localized_value != self._app.ui.text("app.status.ready") and monotonic() < self._status_override_until:
            return
        self.set_status_text(
            localized_value,
            busy=value.startswith(("fetching ", "extracting ", "classifying ", "translating ", "summarizing ")),
        )
        self._call_from_thread_if_ready(self._app.refresh_view)

    def set_status_text(
        self,
        value: str,
        *,
        busy: bool | None = None,
        hold_seconds: float = 0.0,
    ) -> None:
        self.status_text = value
        self._status_busy = self._status_busy_for(value) if busy is None else busy
        self._status_override_until = monotonic() + hold_seconds if hold_seconds > 0 else 0.0

    @staticmethod
    def _status_busy_for(value: str) -> bool:
        return value.startswith(("fetching ", "extracting ", "classifying ", "translating ", "summarizing "))

    def shutdown(self) -> None:
        self._app._shutdown_requested = True
        cancellation = self._cancellation
        if cancellation is not None:
            cancellation.cancel()
        self._dismiss_confirm_screen(False)
