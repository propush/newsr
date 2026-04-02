from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from ...ui_text import UILocalizer


WatchTopicResult = tuple[str, str | None]
ScheduleValidatorFunc = Callable[[str], tuple[str | None, str | None]]


class WatchTopicDialogScreen(ModalScreen[WatchTopicResult | None]):
    CSS = """
    WatchTopicDialogScreen {
        background: transparent;
    }
    #watch-topic-dialog-shell {
        width: 80;
        height: auto;
        margin: 6 8;
        border: heavy $primary;
        background: $background;
    }
    #watch-topic-dialog-header {
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #watch-topic-dialog-body {
        padding: 1 2 0 2;
        color: $foreground;
    }
    .watch-topic-field {
        margin: 1 2 0 2;
    }
    #watch-topic-dialog-error {
        min-height: 1;
        padding: 0 2;
        color: $error;
    }
    #watch-topic-dialog-buttons {
        height: auto;
        padding: 0 2 1 2;
    }
    #watch-topic-dialog-confirm {
        margin-right: 1;
    }
    """

    BINDINGS = []
    _FOCUS_ORDER = (
        "watch-topic-name-input",
        "watch-topic-schedule-input",
        "watch-topic-dialog-confirm",
        "watch-topic-dialog-cancel",
    )

    def __init__(
        self,
        ui: UILocalizer,
        *,
        title: str,
        body: str,
        topic_name: str,
        update_schedule: str | None,
        topic_placeholder: str,
        schedule_placeholder: str,
        confirm_label: str,
        cancel_label: str,
        schedule_validator: ScheduleValidatorFunc,
    ) -> None:
        super().__init__()
        self._ui = ui
        self._title = title
        self._body = body
        self._topic_name = topic_name
        self._update_schedule = update_schedule or ""
        self._topic_placeholder = topic_placeholder
        self._schedule_placeholder = schedule_placeholder
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label
        self._schedule_validator = schedule_validator
        self._bindings = BindingsMap(self._build_bindings())

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            Binding("tab", "focus_next_control", show=False),
            Binding("shift+tab", "focus_previous_control", show=False),
            Binding("left", "focus_previous_control", show=False),
            Binding("right", "focus_next_control", show=False),
            Binding("up", "focus_previous_control", show=False),
            Binding("down", "focus_next_control", show=False),
            ("enter", "activate_focused", self._confirm_label),
            ("escape", "cancel", self._cancel_label),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="watch-topic-dialog-shell"):
            yield Static(self._title, id="watch-topic-dialog-header")
            yield Static(self._body, id="watch-topic-dialog-body")
            yield Input(
                value=self._topic_name,
                placeholder=self._topic_placeholder,
                id="watch-topic-name-input",
                classes="watch-topic-field",
            )
            yield Input(
                value=self._update_schedule,
                placeholder=self._schedule_placeholder,
                id="watch-topic-schedule-input",
                classes="watch-topic-field",
            )
            yield Static("", id="watch-topic-dialog-error")
            with Horizontal(id="watch-topic-dialog-buttons"):
                yield Button(self._confirm_label, id="watch-topic-dialog-confirm", variant="primary")
                yield Button(self._cancel_label, id="watch-topic-dialog-cancel")

    def on_mount(self) -> None:
        self.query_one("#watch-topic-name-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "watch-topic-dialog-confirm":
            self._submit()
            return
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in {"watch-topic-name-input", "watch-topic-schedule-input"}:
            self._submit()

    def action_activate_focused(self) -> None:
        focused_id = self._focused_control_id()
        if focused_id == "watch-topic-dialog-cancel":
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
        topic_name = self.query_one("#watch-topic-name-input", Input).value.strip()
        if not topic_name:
            self.query_one("#watch-topic-dialog-error", Static).update(
                self._ui.text("watch_topic.error.topic_required")
            )
            self.query_one("#watch-topic-name-input", Input).focus()
            return
        schedule_value = self.query_one("#watch-topic-schedule-input", Input).value
        normalized_schedule, error = self._schedule_validator(schedule_value)
        if error:
            self.query_one("#watch-topic-dialog-error", Static).update(error)
            self.query_one("#watch-topic-schedule-input", Input).focus()
            return
        self.dismiss((topic_name, normalized_schedule))

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
