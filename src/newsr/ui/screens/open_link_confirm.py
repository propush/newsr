from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class OpenLinkConfirmScreen(ModalScreen[None]):
    CSS = """
    OpenLinkConfirmScreen {
        background: transparent;
    }
    #open-link-shell {
        width: 72;
        height: auto;
        margin: 8 10;
        border: heavy $primary;
        background: $background;
    }
    #open-link-header {
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #open-link-body {
        padding: 1 2;
        color: $foreground;
    }
    #open-link-buttons {
        height: auto;
        padding: 0 2 1 2;
    }
    #open-link-open {
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("enter", "confirm_open", "Open"),
        Binding("o", "confirm_open", "Open", show=False),
        ("escape", "close_overlay", "Cancel"),
    ]

    def __init__(self, source_title: str, url: str) -> None:
        super().__init__()
        self.source_title = source_title
        self.url = url

    def compose(self) -> ComposeResult:
        with Vertical(id="open-link-shell"):
            yield Static("Open Source Link", id="open-link-header")
            yield Static(
                f"Open this source in your browser?\n\nTitle: {self.source_title}\nURL: {self.url}",
                id="open-link-body",
            )
            with Horizontal(id="open-link-buttons"):
                yield Button("Open", id="open-link-open", variant="primary")
                yield Button("Cancel", id="open-link-cancel")

    def on_mount(self) -> None:
        self.query_one("#open-link-open", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "open-link-open":
            self.app.confirm_open_link()
            return
        self.app.close_open_link_confirm()

    def action_confirm_open(self) -> None:
        self.app.confirm_open_link()

    def action_close_overlay(self) -> None:
        self.app.close_open_link_confirm()
