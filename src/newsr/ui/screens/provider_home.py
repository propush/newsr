from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

from ...ui_text import UILocalizer
from ..group_headers import framed_group_header_text


@dataclass(slots=True)
class ProviderHomeRow:
    scope_id: str | None
    display_name: str
    unread_count: int
    total_count: int
    provider_type: str = "http"
    is_group_header: bool = False


class ProviderHomeScreen(ModalScreen[None]):
    CSS = """
    ProviderHomeScreen {
        background: transparent;
    }
    #provider-home-shell {
        height: 1fr;
        border: heavy $primary;
        background: $background;
    }
    #provider-home-table {
        height: 1fr;
        background: $background;
        color: $foreground;
        overflow-y: scroll;
        overflow-x: auto;
        scrollbar-size-vertical: 1;
        scrollbar-size-horizontal: 1;
        scrollbar-background: $panel;
        scrollbar-background-hover: $panel;
        scrollbar-background-active: $panel;
        scrollbar-color: $accent;
        scrollbar-color-hover: $primary;
        scrollbar-color-active: $primary;
        scrollbar-gutter: stable;
        scrollbar-visibility: visible;
    }
    #provider-home-empty {
        height: 1fr;
        content-align: center middle;
        color: $secondary;
    }
    #provider-home-selection {
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $background;
        border-top: solid $primary;
    }
    #provider-home-status {
        height: 1;
        padding: 0 1;
        color: $success;
        background: $background;
    }
    #provider-home-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $background;
    }
    """

    BINDINGS = []

    def __init__(
        self,
        ui: UILocalizer,
        rows: list[ProviderHomeRow],
        selected_scope_id: str,
    ) -> None:
        super().__init__()
        self._bindings.bind("c", "show_source_manager", ui.text("app.binding.sources"))
        self._bindings.bind("ctrl+p", "show_command_palette", show=False)
        self._bindings.bind("w", "watch_topic", ui.text("app.binding.watch_topic"))
        self._bindings.bind("d", "refresh_articles", ui.text("app.binding.download"))
        self._bindings.bind("h", "show_help", ui.text("app.binding.help"))
        self._bindings.bind("space", "open_selected_provider", ui.text("app.binding.space"), show=False)
        self._ui = ui
        self._rows = rows
        self._selected_scope_id = selected_scope_id

    def compose(self) -> ComposeResult:
        with Vertical(id="provider-home-shell"):
            yield DataTable(id="provider-home-table", cursor_type="row")
            yield Static(self._ui.text("provider_home.empty"), id="provider-home-empty")
            yield Static(id="provider-home-selection")
            yield Static(id="provider-home-status")
            yield Static(self._ui.text("provider_home.hint"), id="provider-home-hint")

    def on_mount(self) -> None:
        self._configure_table()
        self._refresh_rows()

    def on_resize(self, event: Resize) -> None:
        self._refresh_rows()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not self._rows:
            return
        row = self._rows[event.cursor_row]
        if row.scope_id is None:
            return
        self.app.open_scope(row.scope_id)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._update_status(event.cursor_row)

    def set_rows(self, rows: list[ProviderHomeRow], *, selected_scope_id: str) -> None:
        self._rows = rows
        self._selected_scope_id = selected_scope_id
        if self.is_mounted:
            self._refresh_rows()

    @property
    def selected_scope_id(self) -> str:
        return self._selected_scope_id

    def action_show_source_manager(self) -> None:
        self.app.action_show_source_manager()

    def action_refresh_articles(self) -> None:
        self.app.action_download_articles()

    def action_watch_topic(self) -> None:
        self.app.action_watch_topic()

    def action_show_help(self) -> None:
        self.app.action_show_help()

    def action_show_command_palette(self) -> None:
        self.app.action_command_palette()

    def action_open_selected_provider(self) -> None:
        table = self.query_one("#provider-home-table", DataTable)
        if not self._rows or table.cursor_row < 0 or table.cursor_row >= len(self._rows):
            return
        row = self._rows[table.cursor_row]
        if row.scope_id is None:
            return
        self.app.open_scope(row.scope_id)

    def _configure_table(self) -> None:
        table = self.query_one("#provider-home-table", DataTable)
        table.zebra_stripes = True
        table.show_header = True
        table.show_cursor = True
        table.show_row_labels = False

    def _refresh_rows(self) -> None:
        table = self.query_one("#provider-home-table", DataTable)
        empty = self.query_one("#provider-home-empty", Static)
        previous_scope_id = self._selected_scope_id if self._rows else None
        table.clear(columns=True)
        table.add_column(self._ui.text("provider_home.table.provider"), key="provider", width=self._provider_width(table))
        table.add_column(self._ui.text("provider_home.table.unread"), key="unread", width=self._counter_width())
        table.add_column(self._ui.text("provider_home.table.total"), key="total", width=self._counter_width())
        if not self._rows:
            table.display = False
            empty.display = True
            self.query_one("#provider-home-selection", Static).update(self._ui.text("provider_home.status.empty"))
            return

        table.display = True
        empty.display = False
        selected_index = 0
        provider_width = self._provider_width(table)
        for index, row in enumerate(self._rows):
            table.add_row(
                self._provider_cell(row, provider_width=provider_width),
                "" if row.is_group_header else f"{row.unread_count:>3}",
                "" if row.is_group_header else f"{row.total_count:>3}",
                key=row.scope_id or f"group:{row.display_name}",
            )
            if row.scope_id == previous_scope_id:
                selected_index = index
        selected_index = self._first_selectable_row_index(selected_index)
        table.move_cursor(row=selected_index, column=0, animate=False, scroll=True)
        table.focus()
        self._update_status(selected_index)

    @staticmethod
    def _counter_width() -> int:
        return 6

    def _provider_width(self, table: DataTable) -> int:
        table_padding = 2 * table.cell_padding
        reserved = (self._counter_width() * 2) + (table_padding * 3) + 6
        return max(12, self.size.width - reserved)

    def _update_status(self, index: int) -> None:
        if not self._rows or index < 0 or index >= len(self._rows):
            self.query_one("#provider-home-selection", Static).update(self._ui.text("provider_home.status.empty"))
            return
        row = self._rows[index]
        if row.scope_id is None:
            self.query_one("#provider-home-selection", Static).update(self._ui.text("provider_home.status.empty"))
            return
        self._selected_scope_id = row.scope_id
        self.query_one("#provider-home-selection", Static).update(
            self._ui.text(
                "provider_home.status.selection",
                provider=row.display_name,
                unread=row.unread_count,
                total=row.total_count,
            )
        )

    def set_app_status(self, status_text: str) -> None:
        self.query_one("#provider-home-status", Static).update(status_text)

    @staticmethod
    def _provider_cell(row: ProviderHomeRow, *, provider_width: int) -> Text | str:
        if row.is_group_header:
            return framed_group_header_text(row.display_name, provider_width)
        return row.display_name

    def _first_selectable_row_index(self, preferred_index: int) -> int:
        if 0 <= preferred_index < len(self._rows) and not self._rows[preferred_index].is_group_header:
            return preferred_index
        for index, row in enumerate(self._rows):
            if not row.is_group_header:
                return index
        return 0
