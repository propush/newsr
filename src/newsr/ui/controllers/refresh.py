from __future__ import annotations

from threading import Thread
from time import monotonic
from typing import TYPE_CHECKING

from ...cancellation import RefreshCancellation

if TYPE_CHECKING:
    from ..app import NewsReaderApp


class RefreshController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self.in_progress = False
        self._thread: Thread | None = None
        self._cancellation: RefreshCancellation | None = None
        self._auto_select_first_ready_article = False
        self.status_text: str = app.ui.text("app.status.ready")
        self._status_busy = False
        self._status_override_until = 0.0

    @property
    def status_busy(self) -> bool:
        return self._status_busy

    def start(self) -> None:
        if self.in_progress or self._app._shutdown_requested:
            return
        self.in_progress = True
        self._app._navigation._auto_fetch_armed = False
        self._auto_select_first_ready_article = not self._app.articles
        self._cancellation = RefreshCancellation()
        self._thread = self._launch_thread()

    def _launch_thread(self) -> Thread:
        thread = Thread(target=self._run, name="newsr-refresh", daemon=True)
        thread.start()
        return thread

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
