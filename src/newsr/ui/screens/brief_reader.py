from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Markdown, Static

from ...ui_text import UILocalizer


class BriefReaderScreen(ModalScreen[None]):
    CSS = """
    BriefReaderScreen {
        background: transparent;
    }
    #brief-reader-shell {
        height: 1fr;
        border: heavy $primary;
        background: $background;
    }
    #brief-reader-header {
        height: auto;
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #brief-reader-pane {
        height: 1fr;
        align: center top;
        overflow-y: scroll;
        scrollbar-size-vertical: 1;
        scrollbar-background: $panel;
        scrollbar-background-hover: $panel;
        scrollbar-background-active: $panel;
        scrollbar-color: $accent;
        scrollbar-color-hover: $primary;
        scrollbar-color-active: $primary;
        scrollbar-gutter: stable;
        scrollbar-visibility: visible;
    }
    #brief-reader-body {
        width: 1fr;
        max-width: 82;
        padding: 0 2 1 2;
        color: $foreground;
    }
    #brief-reader-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    """

    BINDINGS = []

    def __init__(self, ui: UILocalizer, report: str) -> None:
        super().__init__()
        self._ui = ui
        self._report = report
        self._bindings = BindingsMap(self._build_bindings())

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            ("escape", "close_reader", self._ui.text("brief_reader.binding.close")),
            Binding("up", "scroll_up_report", show=False),
            Binding("down", "scroll_down_report", show=False),
            Binding("pageup,b", "page_up_report", self._ui.text("brief_reader.binding.pgup"), show=False),
            Binding("pagedown,space", "page_down_report", self._ui.text("brief_reader.binding.pgdn"), show=False),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="brief-reader-shell"):
            yield Static(self._ui.text("brief_reader.header"), id="brief-reader-header")
            with VerticalScroll(id="brief-reader-pane", can_focus=False):
                yield Markdown(id="brief-reader-body")
            yield Static(self._ui.text("brief_reader.hint"), id="brief-reader-hint")

    def on_mount(self) -> None:
        self.set_content(self._report)

    def set_content(self, value: str) -> None:
        try:
            self.query_one("#brief-reader-body", Markdown).update(value)
            self.query_one("#brief-reader-pane", VerticalScroll).scroll_to(y=0, animate=False)
        except NoMatches:
            return

    def action_close_reader(self) -> None:
        self.app.close_brief_reader()

    def action_scroll_up_report(self) -> None:
        self.query_one("#brief-reader-pane", VerticalScroll).scroll_up(animate=False)

    def action_scroll_down_report(self) -> None:
        self.query_one("#brief-reader-pane", VerticalScroll).scroll_down(animate=False)

    def action_page_up_report(self) -> None:
        self.query_one("#brief-reader-pane", VerticalScroll).scroll_page_up(animate=False)

    def action_page_down_report(self) -> None:
        self.query_one("#brief-reader-pane", VerticalScroll).scroll_page_down(animate=False)
