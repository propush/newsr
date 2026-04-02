from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from ...ui_text import UILocalizer


ValidatorResult = tuple[str | None, str | None]
ValidatorFunc = Callable[[str], ValidatorResult]


class TextInputDialogScreen(ModalScreen[str | None]):
    CSS = """
    TextInputDialogScreen {
        background: transparent;
    }
    #text-input-dialog-shell {
        width: 76;
        height: auto;
        margin: 6 8;
        border: heavy $primary;
        background: $background;
    }
    #text-input-dialog-header {
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #text-input-dialog-body {
        padding: 1 2 0 2;
        color: $foreground;
    }
    #text-input-dialog-input {
        margin: 1 2 0 2;
    }
    #text-input-dialog-error {
        min-height: 1;
        padding: 0 2;
        color: $error;
    }
    #text-input-dialog-buttons {
        height: auto;
        padding: 0 2 1 2;
    }
    #text-input-dialog-confirm {
        margin-right: 1;
    }
    """

    BINDINGS = []
    _FOCUS_ORDER = ("text-input-dialog-input", "text-input-dialog-confirm", "text-input-dialog-cancel")

    def __init__(
        self,
        ui: UILocalizer,
        *,
        title: str,
        body: str,
        initial_value: str,
        placeholder: str,
        confirm_label: str,
        cancel_label: str,
        validator: ValidatorFunc,
    ) -> None:
        super().__init__()
        self._ui = ui
        self._title = title
        self._body = body
        self._initial_value = initial_value
        self._placeholder = placeholder
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label
        self._validator = validator
        self._bindings = BindingsMap(self._build_bindings())

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            Binding("tab", "focus_next_control", show=False),
            Binding("shift+tab", "focus_previous_control", show=False),
            Binding("left", "focus_previous_control", show=False),
            Binding("right", "focus_next_control", show=False),
            ("enter", "activate_focused", self._confirm_label),
            ("escape", "cancel", self._cancel_label),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="text-input-dialog-shell"):
            yield Static(self._title, id="text-input-dialog-header")
            yield Static(self._body, id="text-input-dialog-body")
            yield Input(value=self._initial_value, placeholder=self._placeholder, id="text-input-dialog-input")
            yield Static("", id="text-input-dialog-error")
            with Horizontal(id="text-input-dialog-buttons"):
                yield Button(self._confirm_label, id="text-input-dialog-confirm", variant="primary")
                yield Button(self._cancel_label, id="text-input-dialog-cancel")

    def on_mount(self) -> None:
        self.query_one("#text-input-dialog-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "text-input-dialog-confirm":
            self._submit()
            return
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "text-input-dialog-input":
            self._submit()

    def action_activate_focused(self) -> None:
        focused_id = self._focused_control_id()
        if focused_id == "text-input-dialog-cancel":
            self.dismiss(None)
            return
        self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_focus_next_control(self) -> None:
        self._move_focus(1)

    def action_focus_previous_control(self) -> None:
        self._move_focus(-1)

    def _submit(self) -> None:
        value = self.query_one("#text-input-dialog-input", Input).value
        normalized, error = self._validator(value)
        if error:
            self.query_one("#text-input-dialog-error", Static).update(error)
            self.query_one("#text-input-dialog-input", Input).focus()
            return
        self.dismiss(normalized)

    def _focused_control_id(self) -> str:
        focused = self.app.focused
        focused_id = getattr(focused, "id", None)
        if focused_id in self._FOCUS_ORDER:
            return str(focused_id)
        return self._FOCUS_ORDER[0]

    def _move_focus(self, step: int) -> None:
        current_id = self._focused_control_id()
        current_index = self._FOCUS_ORDER.index(current_id)
        next_index = (current_index + step) % len(self._FOCUS_ORDER)
        self.query_one(f"#{self._FOCUS_ORDER[next_index]}").focus()
