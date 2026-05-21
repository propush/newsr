from __future__ import annotations

import re

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Vertical, VerticalScroll
from textual.content import Content, Span
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Markdown, Static
from textual.widgets._markdown import MarkdownBlock

from ...ui_text import UILocalizer

_ARTICLE_REF_RE = re.compile(r"\[(\d+)\]")
_SCROLL_RESTORE_ATTEMPTS = 30


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

    def __init__(self, ui: UILocalizer, report: str, *, article_count: int = 0) -> None:
        super().__init__()
        self._ui = ui
        self._report = report
        self._article_count = article_count
        self._pending_scroll_restore: int | None = None
        self._scroll_restore_attempts = 0
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
            yield Static(
                self._ui.text("brief_reader.hint_with_jump")
                if self._article_count
                else self._ui.text("brief_reader.hint"),
                id="brief-reader-hint",
            )

    def on_mount(self) -> None:
        self.set_content(self._report)

    def set_content(self, value: str) -> None:
        try:
            self.query_one("#brief-reader-body", Markdown).update(value)
            self.query_one("#brief-reader-pane", VerticalScroll).scroll_to(y=0, animate=False)
            self.call_after_refresh(self._style_article_references)
        except NoMatches:
            return

    def report_scroll_offset(self) -> int:
        try:
            return int(self.query_one("#brief-reader-pane", VerticalScroll).scroll_y)
        except NoMatches:
            return 0

    def restore_scroll_offset(self, offset: int) -> None:
        self._pending_scroll_restore = max(0, offset)
        self._scroll_restore_attempts = _SCROLL_RESTORE_ATTEMPTS
        self.call_after_refresh(self._restore_scroll_if_ready)

    def _restore_scroll_if_ready(self) -> None:
        requested_offset = self._pending_scroll_restore
        if requested_offset is None:
            return
        try:
            pane = self.query_one("#brief-reader-pane", VerticalScroll)
        except NoMatches:
            return
        max_offset = int(pane.max_scroll_y)
        if requested_offset > max_offset and self._scroll_restore_attempts > 0:
            self._scroll_restore_attempts -= 1
            self.set_timer(0.02, self._restore_scroll_if_ready)
            return
        pane.scroll_to(y=min(requested_offset, max_offset), animate=False)
        self._pending_scroll_restore = None
        self._scroll_restore_attempts = 0

    def on_key(self, event: events.Key) -> None:
        if self._article_count <= 0 or event.character is None or not event.character.isdigit():
            return
        event.stop()
        event.prevent_default()
        self.app.show_brief_article_jump(event.character)

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

    def _style_article_references(self) -> None:
        try:
            blocks = list(self.query_one("#brief-reader-body", Markdown).query(MarkdownBlock))
        except NoMatches:
            return
        for block in blocks:
            content = getattr(block, "_content", None)
            if not isinstance(content, Content):
                continue
            styled = _style_article_references(content)
            if styled is not content:
                block.set_content(styled)


def _style_article_references(content: Content) -> Content:
    text = content.plain
    matches = list(_ARTICLE_REF_RE.finditer(text))
    if not matches:
        return content
    spans = list(content.spans)
    spans.extend(Span(match.start(), match.end(), "$accent bold") for match in matches)
    return Content(text, spans=spans)
