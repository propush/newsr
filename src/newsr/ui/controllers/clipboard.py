from __future__ import annotations

import asyncio
import os
from collections import deque
from typing import TYPE_CHECKING

from textual.widgets import Input, TextArea
from textual.worker import Worker

from ...export import ClipboardError, ClipboardManager

if TYPE_CHECKING:
    from ..app import NewsReaderApp


class ClipboardController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self.clipboard = ClipboardManager(timeout=2.0)
        self._pending: deque[str] = deque()
        self._worker: Worker[None] | None = None
        self._closed = False

    def selected_text(self) -> str | None:
        focused = self._app.focused
        if isinstance(focused, (Input, TextArea)) and focused.selected_text:
            return focused.selected_text
        return self._app.screen.get_selected_text()

    def copy_selection(self) -> None:
        text = self.selected_text()
        if text:
            self._app.copy_to_clipboard(text)

    def copy_native(self, text: str) -> None:
        if self._closed or any(os.environ.get(key) for key in ("SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY")):
            return
        self._pending.append(text)
        if self._worker is None:
            self._worker = self._app.run_worker(self._write_pending(), group="clipboard")

    async def _write_pending(self) -> None:
        try:
            while self._pending and not self._closed:
                text = self._pending.popleft()
                try:
                    await asyncio.to_thread(self.clipboard.copy_text, text)
                except ClipboardError as exc:
                    if not self._closed:
                        self._app.notify(
                            self._app.ui.text("clipboard.error", error=str(exc)),
                            severity="warning",
                        )
        finally:
            self._worker = None

    def shutdown(self) -> None:
        self._closed = True
        self._pending.clear()
        if self._worker is not None:
            self._worker.cancel()
