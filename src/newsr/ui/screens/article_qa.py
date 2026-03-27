from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, LoadingIndicator, Markdown, Static


class ArticleQuestionScreen(ModalScreen[None]):
    CSS = """
    ArticleQuestionScreen {
        background: transparent;
    }
    #article-qa-shell {
        margin: 1 0 1 0;
        height: 1fr;
        border: heavy $primary;
        background: $background;
    }
    #article-qa-header {
        height: auto;
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #article-qa-loading {
        height: 1;
        padding: 0 1;
        color: $accent;
        background: $background;
        display: none;
    }
    #article-qa-pane {
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
    #article-qa-body {
        padding: 0 2 1 2;
        color: $foreground;
    }
    #article-qa-sources-label {
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
        display: none;
    }
    #article-qa-source-list {
        height: 7;
        margin: 0 1;
        border: solid $secondary;
        display: none;
    }
    .article-qa-source-item {
        height: auto;
        padding: 0 1;
    }
    #article-qa-input {
        margin: 0 1;
    }
    #article-qa-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    """

    BINDINGS = [
        ("escape", "close_overlay", "Close"),
        Binding("tab", "focus_next_control", "Next", show=False),
        Binding("shift+tab", "focus_previous_control", "Previous", show=False),
        ("pageup", "page_up_overlay", "PgUp"),
        ("pagedown", "page_down_overlay", "PgDn"),
    ]

    def __init__(self, article_title: str) -> None:
        super().__init__()
        self.article_title = article_title
        self.loading = False
        self.status_text = "ready"
        self.body_text = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="article-qa-shell"):
            yield Static(id="article-qa-header")
            yield LoadingIndicator(id="article-qa-loading")
            with VerticalScroll(id="article-qa-pane"):
                yield Markdown(id="article-qa-body", open_links=False)
            yield Static("Sources", id="article-qa-sources-label")
            yield ListView(id="article-qa-source-list")
            yield Input(placeholder="Ask anything about this article", id="article-qa-input")
            yield Static(
                "Enter: ask/open source   Tab: input/sources   Esc: close   PgUp/PgDn: scroll answer",
                id="article-qa-hint",
            )

    def on_mount(self) -> None:
        self.update_header()
        self.set_loading(self.loading)
        self.set_content(self.body_text)
        self.focus_input()

    def focus_input(self) -> None:
        try:
            self.query_one("#article-qa-input", Input).focus()
        except NoMatches:
            return

    def set_loading(self, value: bool) -> None:
        self.loading = value
        try:
            self.query_one("#article-qa-loading", LoadingIndicator).display = value
            self.query_one("#article-qa-input", Input).disabled = value
        except NoMatches:
            return

    def set_status(self, value: str) -> None:
        self.status_text = value
        self.update_header()

    def set_content(self, value: str) -> None:
        self.body_text = value
        try:
            self.query_one("#article-qa-body", Markdown).update(value)
            self.query_one("#article-qa-pane", VerticalScroll).scroll_end(animate=False)
        except NoMatches:
            return

    def set_sources(self, sources: list[tuple[str, str]]) -> None:
        try:
            label = self.query_one("#article-qa-sources-label", Static)
            source_list = self.query_one("#article-qa-source-list", ListView)
        except NoMatches:
            return
        source_list.clear()
        if not sources:
            label.display = False
            source_list.display = False
            return
        label.display = True
        source_list.display = True
        for title, _url in sources:
            source_list.append(
                ListItem(
                    Static(title, classes="article-qa-source-item", markup=False)
                )
            )
        source_list.index = 0

    def set_question(self, value: str) -> None:
        try:
            input_widget = self.query_one("#article-qa-input", Input)
        except NoMatches:
            return
        input_widget.value = value

    def update_header(self) -> None:
        try:
            self.query_one("#article-qa-header", Static).update(
                f"Ask About This Article\nTitle: {self.article_title}\nState: {self.status_text}"
            )
        except NoMatches:
            return

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.app.submit_article_question(event.value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        event.stop()
        source_list = self.query_one("#article-qa-source-list", ListView)
        self.app.open_article_qa_source(source_list.index)

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        event.stop()
        self.app.request_open_link("Source link", event.href)

    def action_focus_next_control(self) -> None:
        try:
            source_list = self.query_one("#article-qa-source-list", ListView)
        except NoMatches:
            self.focus_input()
            return
        if source_list.display and not source_list.has_focus:
            source_list.focus()
            return
        self.focus_input()

    def action_focus_previous_control(self) -> None:
        self.action_focus_next_control()

    def action_close_overlay(self) -> None:
        self.app.close_article_qa()

    def action_page_up_overlay(self) -> None:
        self.query_one("#article-qa-pane", VerticalScroll).scroll_page_up()

    def action_page_down_overlay(self) -> None:
        self.query_one("#article-qa-pane", VerticalScroll).scroll_page_down()
