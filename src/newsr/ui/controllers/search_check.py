from __future__ import annotations

import asyncio
import webbrowser
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import NewsReaderApp


class SearchCheckController:
    """Offers a DuckDuckGo browser check without interrupting the reader."""

    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._pending_url: str | None = None

    @property
    def pending_url(self) -> str | None:
        return self._pending_url

    def offer(self, url: str) -> None:
        self._pending_url = url
        self._app.notify(
            self._app.ui.text("search_check.notice"),
            title=self._app.ui.text("search_check.title"),
            severity="warning",
            timeout=20,
        )

    def open_pending(self) -> None:
        url = self._pending_url
        if url is None:
            self._set_status(self._app.ui.text("search_check.status.none"))
            return
        self._pending_url = None
        self._app.run_worker(self._open_in_browser(url), group="search-check")

    async def _open_in_browser(self, url: str) -> None:
        try:
            opened = await asyncio.to_thread(webbrowser.open, url, 2)
        except Exception as exc:
            status = self._app.ui.text("app.status.browser_open_failed", error=exc)
        else:
            status = (
                self._app.ui.text("search_check.status.opened")
                if opened
                else self._app.ui.text("app.status.browser_not_confirmed")
            )
        self._set_status(status)

    def _set_status(self, value: str) -> None:
        self._app._refresh.set_status_text(value, busy=False, hold_seconds=1.0)
        self._app.refresh_view()
