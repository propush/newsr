from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import BindingsMap
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Static

from ...ui_text import UILocalizer


class HelpScreen(ModalScreen[None]):
    def __init__(self, body: str) -> None:
        super().__init__()
        self._body = body
        self._bindings = BindingsMap([("escape", "close_overlay", "Close help")])

    def compose(self) -> ComposeResult:
        yield Static(self._body, id="help-text")

    def on_key(self, event: Key) -> None:
        event.stop()
        self.dismiss()
        self.app.restore_reader_focus()

    def action_close_overlay(self) -> None:
        self.dismiss()
        self.app.restore_reader_focus()
