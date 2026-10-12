from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Vertical
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

from ...domain.articles import ArticleRecord
from ...ui_text import UILocalizer
from .article_rows import (
    CATEGORY_COLUMN_WIDTH,
    DATE_COLUMN_WIDTH,
    PROVIDER_COLUMN_WIDTH,
    format_short_article_date,
    provider_label,
    title_column_width,
    trimmed_title,
)


@dataclass(frozen=True, slots=True)
class PlaylistRow:
    article: ArticleRecord
    marker: str = ""


class PlaylistScreen(ModalScreen[None]):
    CSS = """
    PlaylistScreen {
        background: $background;
    }
    #playlist-shell {
        height: 1fr;
        border: heavy $primary;
        background: $background;
    }
    #playlist-header {
        height: auto;
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #playlist-table {
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
    #playlist-empty {
        height: 1fr;
        content-align: center middle;
        color: $secondary;
    }
    #playlist-selection {
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    #playlist-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    """

    BINDINGS = []

    def __init__(
        self,
        ui: UILocalizer,
        rows: list[PlaylistRow],
        header_text: str,
        provider_display_names: dict[str, str],
    ) -> None:
        super().__init__()
        self._ui = ui
        self._rows = rows
        self._header_text = header_text
        self._provider_display_names = provider_display_names
        self._bindings = BindingsMap(self._build_bindings())

    def _build_bindings(self) -> list[Binding]:
        return [
            Binding("escape", "close_overlay", self._ui.text("playlist.binding.close")),
            Binding("p,space", "toggle_playback", self._ui.text("playlist.binding.play_pause")),
            Binding("x,delete,backspace", "remove_selected", self._ui.text("playlist.binding.remove")),
            Binding("c", "clear_playlist", self._ui.text("playlist.binding.clear")),
            Binding("right_square_bracket", "skip", show=False),
            Binding("left_square_bracket", "restart", show=False),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="playlist-shell"):
            yield Static(self._header_text, id="playlist-header")
            yield DataTable(id="playlist-table", cursor_type="row")
            yield Static(self._ui.text("playlist.empty"), id="playlist-empty")
            yield Static(id="playlist-selection")
            yield Static(self._ui.text("playlist.hint"), id="playlist-hint")

    def on_mount(self) -> None:
        table = self.query_one("#playlist-table", DataTable)
        table.zebra_stripes = True
        table.show_header = True
        table.show_cursor = True
        self._refresh_rows()

    def on_resize(self, event: Resize) -> None:
        self._refresh_rows()

    def update_rows(self, rows: list[PlaylistRow], header_text: str) -> None:
        if not self.is_mounted:
            self._rows = rows
            self._header_text = header_text
            return
        table = self.query_one("#playlist-table", DataTable)
        previous_row = table.cursor_row if table.row_count else 0
        previous_article_id = self.selected_article_id
        self._rows = rows
        self.update_header(header_text)
        self._refresh_rows(previous_article_id=previous_article_id, previous_row=previous_row)

    def update_header(self, header_text: str) -> None:
        self._header_text = header_text
        if self.is_mounted:
            self.query_one("#playlist-header", Static).update(header_text)

    def restore_navigation_focus(self) -> None:
        self.query_one("#playlist-table", DataTable).focus()

    @property
    def selected_article_id(self) -> str | None:
        table = self.query_one("#playlist-table", DataTable)
        if not self._rows or not table.is_valid_row_index(table.cursor_row):
            return None
        return self._rows[table.cursor_row].article.article_id

    def action_close_overlay(self) -> None:
        self.dismiss()
        self.app.restore_reader_focus()

    def action_toggle_playback(self) -> None:
        self.app.action_toggle_playback()

    def action_remove_selected(self) -> None:
        article_id = self.selected_article_id
        if article_id is not None:
            self.app.playlist_remove(article_id)

    def action_clear_playlist(self) -> None:
        if self._rows:
            self.app.request_clear_playlist()

    def action_skip(self) -> None:
        self.app.action_playlist_skip()

    def action_restart(self) -> None:
        self.app.action_playlist_restart()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not self._rows or event.cursor_row >= len(self._rows):
            return
        self.app.playlist_play_now(self._rows[event.cursor_row].article.article_id)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._update_selection_status(event.cursor_row)

    def _refresh_rows(self, *, previous_article_id: str | None = None, previous_row: int | None = None) -> None:
        table = self.query_one("#playlist-table", DataTable)
        empty = self.query_one("#playlist-empty", Static)
        if previous_row is None:
            previous_row = table.cursor_row if table.row_count else 0
            previous_article_id = self.selected_article_id if table.row_count else None
        title_width = title_column_width(self.size.width)
        table.clear(columns=True)
        table.add_column(" ", width=1, key="marker")
        table.add_column(self._ui.text("quick_nav.table.date"), width=DATE_COLUMN_WIDTH, key="date")
        table.add_column(self._ui.text("quick_nav.table.title"), width=title_width, key="title")
        table.add_column(self._ui.text("quick_nav.table.provider"), width=PROVIDER_COLUMN_WIDTH, key="provider")
        table.add_column(self._ui.text("quick_nav.table.category"), width=CATEGORY_COLUMN_WIDTH, key="category")
        table.display = bool(self._rows)
        empty.display = not self._rows
        for row in self._rows:
            article = row.article
            table.add_row(
                row.marker,
                format_short_article_date(article),
                Text(trimmed_title(article, title_width)),
                Text(provider_label(article, self._provider_display_names)),
                Text(article.category),
                key=article.article_id,
            )
        if not self._rows:
            self._update_selection_status(0)
            return
        selected_index = min(previous_row, len(self._rows) - 1)
        for index, row in enumerate(self._rows):
            if row.article.article_id == previous_article_id:
                selected_index = index
                break
        table.move_cursor(row=selected_index, column=0, animate=False, scroll=True)
        self._update_selection_status(selected_index)
        table.focus()

    def _update_selection_status(self, selected_index: int) -> None:
        selection = self.query_one("#playlist-selection", Static)
        if not self._rows:
            selection.update(self._ui.text("quick_nav.selection", current=0, total=0))
            return
        bounded_index = min(max(selected_index, 0), len(self._rows) - 1)
        selection.update(self._ui.text("quick_nav.selection", current=bounded_index + 1, total=len(self._rows)))
