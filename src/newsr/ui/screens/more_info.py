from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import LoadingIndicator, Markdown, Static

from ...ui_text import UILocalizer


class MoreInfoScreen(ModalScreen[None]):
    CSS = """
    MoreInfoScreen {
        background: transparent;
    }
    #more-info-shell {
        margin: 1 0 1 0;
        height: 1fr;
        border: heavy $primary;
        background: $background;
    }
    #more-info-header {
        height: auto;
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #more-info-loading {
        height: 1;
        padding: 0 1;
        color: $accent;
        background: $background;
        display: none;
    }
    #more-info-pane {
        height: 1fr;
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
    #more-info-body {
        padding: 0 2 1 2;
        color: $foreground;
    }
    #more-info-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    """

    BINDINGS = []

    def __init__(self, ui: UILocalizer, article_title: str) -> None:
        super().__init__()
        self._ui = ui
        self._bindings = BindingsMap(self._build_bindings())
        self.article_title = article_title
        self.loading = True
        self.status_text = "loading..."
        self.body_text = ""

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            ("escape", "close_overlay", self._ui.text("more_info.binding.close")),
            ("m", "refresh_overlay", self._ui.text("more_info.binding.refresh")),
            ("left", "previous_article", self._ui.text("more_info.binding.previous")),
            ("right", "next_article", self._ui.text("more_info.binding.next")),
            Binding("b", "page_up_overlay", self._ui.text("more_info.binding.back"), show=False),
            Binding("space", "page_down_overlay", self._ui.text("more_info.binding.space"), show=False),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="more-info-shell"):
            yield Static(id="more-info-header")
            yield LoadingIndicator(id="more-info-loading")
            with VerticalScroll(id="more-info-pane"):
                yield Markdown(id="more-info-body")
            yield Static(self._ui.text("more_info.hint"), id="more-info-hint")

    def on_mount(self) -> None:
        self.update_header()
        self.set_loading(self.loading)
        self.set_content(self.body_text)

    def set_loading(self, value: bool) -> None:
        self.loading = value
        try:
            self.query_one("#more-info-loading", LoadingIndicator).display = value
        except NoMatches:
            return

    def set_status(self, value: str) -> None:
        self.status_text = value
        self.update_header()

    def set_content(self, value: str) -> None:
        self.body_text = value
        try:
            self.query_one("#more-info-body", Markdown).update(value)
            self.query_one("#more-info-pane", VerticalScroll).scroll_to(y=0, animate=False)
        except NoMatches:
            return

    def update_header(self) -> None:
        try:
            self.query_one("#more-info-header", Static).update(
                self._ui.text("more_info.header", title=self.article_title, state=self._ui.status(self.status_text))
            )
        except NoMatches:
            return

    def action_close_overlay(self) -> None:
        self.app.close_more_info()

    def action_refresh_overlay(self) -> None:
        self.app.refresh_more_info(force_refresh=True)

    def action_previous_article(self) -> None:
        self.app.action_previous_article()

    def action_next_article(self) -> None:
        self.app.action_next_article()

    def action_page_up_overlay(self) -> None:
        self.query_one("#more-info-pane", VerticalScroll).scroll_page_up()

    def action_page_down_overlay(self) -> None:
        self.query_one("#more-info-pane", VerticalScroll).scroll_page_down()
