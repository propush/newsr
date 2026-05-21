from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from ...ui_text import UILocalizer


class BriefArticleJumpScreen(ModalScreen[None]):
    CSS = """
    BriefArticleJumpScreen {
        background: transparent;
    }
    #brief-article-jump-shell {
        width: 52;
        height: auto;
        margin: 6 8;
        border: heavy $primary;
        background: $background;
    }
    #brief-article-jump-header {
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #brief-article-jump-body {
        padding: 1 2 0 2;
        color: $foreground;
    }
    #brief-article-jump-input {
        margin: 1 2 0 2;
    }
    #brief-article-jump-error {
        min-height: 1;
        padding: 0 2;
        color: $error;
    }
    #brief-article-jump-buttons {
        height: auto;
        padding: 0 2 1 2;
    }
    #brief-article-jump-confirm {
        margin-right: 1;
    }
    """

    BINDINGS = []
    _FOCUS_ORDER = (
        "brief-article-jump-input",
        "brief-article-jump-confirm",
        "brief-article-jump-cancel",
    )

    def __init__(self, ui: UILocalizer, *, initial_value: str, max_number: int) -> None:
        super().__init__()
        self._ui = ui
        self._initial_value = initial_value
        self._max_number = max_number
        self._bindings = BindingsMap(self._build_bindings())

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            Binding("tab", "focus_next_control", show=False),
            Binding("shift+tab", "focus_previous_control", show=False),
            Binding("left", "focus_previous_control", show=False),
            Binding("right", "focus_next_control", show=False),
            ("enter", "activate_focused", self._ui.text("brief_jump.binding.jump")),
            ("escape", "cancel", self._ui.text("brief_jump.binding.cancel")),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="brief-article-jump-shell"):
            yield Static(self._ui.text("brief_jump.header"), id="brief-article-jump-header")
            yield Static(
                self._ui.text("brief_jump.body", max_number=self._max_number),
                id="brief-article-jump-body",
            )
            yield Input(value=self._initial_value, id="brief-article-jump-input")
            yield Static("", id="brief-article-jump-error")
            with Horizontal(id="brief-article-jump-buttons"):
                yield Button(
                    self._ui.text("brief_jump.button.jump"),
                    id="brief-article-jump-confirm",
                    variant="primary",
                )
                yield Button(self._ui.text("brief_jump.button.cancel"), id="brief-article-jump-cancel")

    def on_mount(self) -> None:
        input_widget = self.query_one("#brief-article-jump-input", Input)
        input_widget.focus()
        input_widget.cursor_position = len(input_widget.value)

    def on_key(self, event: events.Key) -> None:
        if event.key != "escape":
            return
        event.stop()
        event.prevent_default()
        self.action_cancel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "brief-article-jump-confirm":
            self._submit()
            return
        self.action_cancel()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "brief-article-jump-input":
            return
        digits = "".join(character for character in event.value if character.isdigit())
        if digits != event.value:
            event.input.value = digits

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "brief-article-jump-input":
            self._submit()

    def action_activate_focused(self) -> None:
        if self._focused_control_id() == "brief-article-jump-cancel":
            self.action_cancel()
            return
        self._submit()

    def action_cancel(self) -> None:
        self.app.close_brief_article_jump(cancelled=True)

    def action_focus_next_control(self) -> None:
        self._move_focus(1)

    def action_focus_previous_control(self) -> None:
        self._move_focus(-1)

    def _submit(self) -> None:
        input_widget = self.query_one("#brief-article-jump-input", Input)
        value = input_widget.value.strip()
        error = self._validation_error(value)
        if error is not None:
            self.query_one("#brief-article-jump-error", Static).update(error)
            input_widget.focus()
            return
        self.app.open_brief_article_by_number(int(value))

    def _validation_error(self, value: str) -> str | None:
        if not value:
            return self._ui.text("brief_jump.error.empty")
        if not value.isdigit():
            return self._ui.text("brief_jump.error.number")
        number = int(value)
        if number <= 0 or number > self._max_number:
            return self._ui.text("brief_jump.error.range", max_number=self._max_number)
        return None

    def _focused_control_id(self) -> str:
        focused_id = getattr(self.app.focused, "id", None)
        if focused_id in self._FOCUS_ORDER:
            return str(focused_id)
        return self._FOCUS_ORDER[0]

    def _move_focus(self, step: int) -> None:
        current_id = self._focused_control_id()
        current_index = self._FOCUS_ORDER.index(current_id)
        next_index = (current_index + step) % len(self._FOCUS_ORDER)
        self.query_one(f"#{self._FOCUS_ORDER[next_index]}").focus()
