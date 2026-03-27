from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ...export import ExportAction


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

    BINDINGS = [
        Binding("1", "choose_save_png", "Save PNG", show=False),
        Binding("2", "choose_copy_png", "Copy PNG", show=False),
        Binding("3", "choose_save_markdown", "Save MD", show=False),
        Binding("4", "choose_copy_markdown", "Copy MD", show=False),
        ("escape", "close_overlay", "Cancel"),
    ]

    def __init__(self, article_title: str, mode_label: str) -> None:
        super().__init__()
        self.article_title = article_title
        self.mode_label = mode_label

    def compose(self) -> ComposeResult:
        with Vertical(id="export-shell"):
            yield Static("Export Current View", id="export-header")
            yield Static(
                f"Title: {self.article_title}\nMode: {self.mode_label}\n\n"
                "1: Save PNG   2: Copy PNG\n"
                "3: Save Markdown   4: Copy Markdown",
                id="export-body",
            )
            with Vertical(id="export-buttons"):
                with Horizontal(classes="export-row"):
                    yield Button("Save PNG", id="export-save-png", variant="primary")
                    yield Button("Copy PNG", id="export-copy-png")
                with Horizontal(classes="export-row"):
                    yield Button("Save Markdown", id="export-save-markdown")
                    yield Button("Copy Markdown", id="export-copy-markdown")
                with Horizontal(classes="export-row"):
                    yield Button("Cancel", id="export-cancel")

    def on_mount(self) -> None:
        self.query_one("#export-save-png", Button).focus()

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

    def action_close_overlay(self) -> None:
        self.app.close_export_screen()
