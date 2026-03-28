from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static

from ...ui_text import UILocalizer


class HelpScreen(ModalScreen[None]):
    def __init__(self, ui: UILocalizer) -> None:
        super().__init__()
        self._ui = ui

    def compose(self) -> ComposeResult:
        yield Static(self._ui.text("help.body"), id="help-text")

    def on_key(self) -> None:
        self.dismiss()
