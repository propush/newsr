from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static


class HelpScreen(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        yield Static(
            "Left/Right: previous/next article\n"
            "Up/Down/PgUp/PgDn/B: scroll\n"
            "Space: page down or next article\n"
            "S: toggle summary\n"
            "M: more info\n"
            "?: ask about article\n"
            "L: article list\n"
            "C: sources\n"
            "E: export current view\n"
            "O: open article in browser\n"
            "D: download new articles\n"
            "Ctrl+P: command palette / choose theme\n"
            "H: help\n"
            "Q: quit",
            id="help-text",
        )

    def on_key(self) -> None:
        self.dismiss()
