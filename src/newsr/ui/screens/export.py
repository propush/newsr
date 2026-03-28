from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ...export import ExportAction
from ...ui_text import UILocalizer


class ExportScreen(ModalScreen[None]):
    CSS = """
    ExportScreen {
        background: transparent;
    }
    #export-shell {
        width: 72;
        height: auto;
        margin: 6 10;
        border: heavy $primary;
        background: $background;
    }
    #export-header {
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #export-body {
        padding: 1 2;
        color: $foreground;
    }
    #export-buttons {
        height: auto;
        padding: 0 2 1 2;
        layout: vertical;
    }
    .export-row {
        height: auto;
        margin-bottom: 1;
    }
    #export-shell Button {
        width: 1fr;
    }
    """

    BINDINGS = []
    _DEFAULT_FOCUS_ID = "export-save-png"
    _HORIZONTAL_FOCUS = {
        "left": {
            "export-copy-png": "export-save-png",
            "export-copy-markdown": "export-save-markdown",
        },
        "right": {
            "export-save-png": "export-copy-png",
            "export-save-markdown": "export-copy-markdown",
        },
    }
    _VERTICAL_FOCUS = {
        "up": {
            "export-save-markdown": "export-save-png",
            "export-copy-markdown": "export-copy-png",
        },
        "down": {
            "export-save-png": "export-save-markdown",
            "export-copy-png": "export-copy-markdown",
            "export-save-markdown": "export-cancel",
            "export-copy-markdown": "export-cancel",
        },
    }

    def __init__(self, ui: UILocalizer, article_title: str, mode_label: str) -> None:
        super().__init__()
        self._ui = ui
        self._bindings = BindingsMap(self._build_bindings())
        self.article_title = article_title
        self.mode_label = mode_label
        self._cancel_return_id = "export-save-markdown"

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            Binding("1", "choose_save_png", self._ui.text("export.binding.save_png"), show=False),
            Binding("2", "choose_copy_png", self._ui.text("export.binding.copy_png"), show=False),
            Binding("3", "choose_save_markdown", self._ui.text("export.binding.save_markdown"), show=False),
            Binding("4", "choose_copy_markdown", self._ui.text("export.binding.copy_markdown"), show=False),
            Binding("left", "focus_left", show=False),
            Binding("right", "focus_right", show=False),
            Binding("up", "focus_up", show=False),
            Binding("down", "focus_down", show=False),
            ("escape", "close_overlay", self._ui.text("export.binding.cancel")),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="export-shell"):
            yield Static(self._ui.text("export.header"), id="export-header")
            yield Static(self._ui.text("export.body", title=self.article_title, mode=self.mode_label), id="export-body")
            with Vertical(id="export-buttons"):
                with Horizontal(classes="export-row"):
                    yield Button(self._ui.text("export.button.save_png"), id="export-save-png", variant="primary")
                    yield Button(self._ui.text("export.button.copy_png"), id="export-copy-png")
                with Horizontal(classes="export-row"):
                    yield Button(self._ui.text("export.button.save_markdown"), id="export-save-markdown")
                    yield Button(self._ui.text("export.button.copy_markdown"), id="export-copy-markdown")
                with Horizontal(classes="export-row"):
                    yield Button(self._ui.text("export.button.cancel"), id="export-cancel")

    def on_mount(self) -> None:
        self.query_one(f"#{self._DEFAULT_FOCUS_ID}", Button).focus()

    def _focused_button_id(self) -> str:
        focused = self.app.focused
        if isinstance(focused, Button) and focused.id is not None:
            return focused.id
        return self._DEFAULT_FOCUS_ID

    def _focus_button(self, button_id: str) -> None:
        self.query_one(f"#{button_id}", Button).focus()

    def _move_focus(self, direction: str) -> None:
        current_id = self._focused_button_id()
        if direction == "down" and current_id in {"export-save-markdown", "export-copy-markdown"}:
            self._cancel_return_id = current_id
        if direction == "up" and current_id == "export-cancel":
            target_id = self._cancel_return_id
        else:
            focus_map = self._HORIZONTAL_FOCUS.get(direction) or self._VERTICAL_FOCUS.get(direction, {})
            target_id = focus_map.get(current_id, current_id)
        if target_id != current_id:
            self._focus_button(target_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button_id = event.button.id
        if button_id == "export-save-png":
            self.app.run_export_action(ExportAction.SAVE_PNG)
            return
        if button_id == "export-copy-png":
            self.app.run_export_action(ExportAction.COPY_PNG)
            return
        if button_id == "export-save-markdown":
            self.app.run_export_action(ExportAction.SAVE_MARKDOWN)
            return
        if button_id == "export-copy-markdown":
            self.app.run_export_action(ExportAction.COPY_MARKDOWN)
            return
        self.app.close_export_screen()

    def action_choose_save_png(self) -> None:
        self.app.run_export_action(ExportAction.SAVE_PNG)

    def action_choose_copy_png(self) -> None:
        self.app.run_export_action(ExportAction.COPY_PNG)

    def action_choose_save_markdown(self) -> None:
        self.app.run_export_action(ExportAction.SAVE_MARKDOWN)

    def action_choose_copy_markdown(self) -> None:
        self.app.run_export_action(ExportAction.COPY_MARKDOWN)

    def action_focus_left(self) -> None:
        self._move_focus("left")

    def action_focus_right(self) -> None:
        self._move_focus("right")

    def action_focus_up(self) -> None:
        self._move_focus("up")

    def action_focus_down(self) -> None:
        self._move_focus("down")

    def action_close_overlay(self) -> None:
        self.app.close_export_screen()
