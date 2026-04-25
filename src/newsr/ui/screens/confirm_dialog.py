from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ...ui_text import UILocalizer


class ConfirmDialogScreen(ModalScreen[bool]):
    CSS = """
    ConfirmDialogScreen {
        background: transparent;
    }
    #confirm-dialog-shell {
        width: 72;
        height: auto;
        margin: 8 10;
        border: heavy $primary;
        background: $background;
    }
    #confirm-dialog-header {
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #confirm-dialog-body {
        padding: 1 2;
        color: $foreground;
    }
    #confirm-dialog-buttons {
        height: auto;
        padding: 0 2 1 2;
    }
    #confirm-dialog-confirm {
        margin-right: 1;
    }
    """

    BINDINGS = []
    _FOCUS_ORDER = ("confirm-dialog-confirm", "confirm-dialog-cancel")

    def __init__(
        self,
        ui: UILocalizer,
        *,
        title: str,
        body: str,
        confirm_label: str,
        cancel_label: str,
    ) -> None:
        super().__init__()
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label
        self._ui = ui
        self._bindings = BindingsMap(self._build_bindings())
        self._title = title
        self._body = body

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            ("enter", "activate_focused", self._confirm_label),
            Binding("y", "confirm", self._confirm_label, show=False),
            Binding("tab", "focus_next_control", show=False),
            Binding("shift+tab", "focus_previous_control", show=False),
            Binding("left", "focus_previous_control", show=False),
            Binding("right", "focus_next_control", show=False),
            ("escape", "cancel", self._cancel_label),
            Binding("n", "cancel", self._cancel_label, show=False),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog-shell"):
            yield Static(self._title, id="confirm-dialog-header")
            yield Static(self._body, id="confirm-dialog-body")
            with Horizontal(id="confirm-dialog-buttons"):
                yield Button(self._confirm_label, id="confirm-dialog-confirm", variant="primary")
                yield Button(self._cancel_label, id="confirm-dialog-cancel")

    def on_mount(self) -> None:
        self.query_one("#confirm-dialog-confirm", Button).focus()

    def _focused_button_id(self) -> str:
        focused = self.app.focused
        if isinstance(focused, Button) and focused.id in self._FOCUS_ORDER:
            return focused.id
        return self._FOCUS_ORDER[0]

    def _focus_button(self, button_id: str) -> None:
        self.query_one(f"#{button_id}", Button).focus()

    def _move_focus(self, step: int) -> None:
        current_id = self._focused_button_id()
        current_index = self._FOCUS_ORDER.index(current_id)
        next_index = (current_index + step) % len(self._FOCUS_ORDER)
        self._focus_button(self._FOCUS_ORDER[next_index])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "confirm-dialog-confirm":
            self._dismiss(True)
            return
        self._dismiss(False)

    def action_activate_focused(self) -> None:
        if self._focused_button_id() == "confirm-dialog-cancel":
            self._dismiss(False)
            return
        self._dismiss(True)

    def action_confirm(self) -> None:
        self._dismiss(True)

    def action_cancel(self) -> None:
        self._dismiss(False)

    def action_focus_next_control(self) -> None:
        self._move_focus(1)

    def action_focus_previous_control(self) -> None:
        self._move_focus(-1)

    def _dismiss(self, result: bool) -> None:
        self.dismiss(result)
        self.app.restore_navigation_focus()
