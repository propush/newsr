from __future__ import annotations

from threading import Thread

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

from ...domain import ProviderRecord, ProviderTarget


class SourceSelectionScreen(ModalScreen[None]):
    CSS = """
    SourceSelectionScreen {
        background: transparent;
    }
    #source-shell {
        margin: 1 0 1 0;
        height: 1fr;
        border: heavy $primary;
        background: $background;
    }
    #source-header {
        height: auto;
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #source-status {
        height: auto;
        padding: 0 1;
        color: $secondary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #source-loading {
        height: 1fr;
        content-align: center middle;
        color: $secondary;
    }
    #source-error {
        height: 1fr;
        content-align: center middle;
        color: $error;
        padding: 1 2;
    }
    #source-content {
        height: 1fr;
    }
    .source-table {
        height: 1fr;
        width: 1fr;
        border: none;
        padding: 0 1;
        background: $background;
        scrollbar-size-vertical: 1;
        scrollbar-background: $panel;
        scrollbar-background-hover: $panel;
        scrollbar-background-active: $panel;
        scrollbar-color: $accent;
        scrollbar-color-hover: $primary;
        scrollbar-color-active: $primary;
        scrollbar-gutter: stable;
        scrollbar-visibility: visible;
        color: $foreground;
        & > .datatable--header {
            display: none;
        }
        &:focus > .datatable--cursor {
            background: $primary;
            color: $background;
        }
    }
    #source-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    """

    BINDINGS = [
        ("escape", "close_overlay", "Close"),
        Binding("tab", "switch_pane", "Pane", show=False),
        Binding("space", "toggle_item", "Toggle", show=False),
        ("r", "refresh_catalog", "Refresh"),
        ("a", "save_selection", "Apply"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._providers: list[ProviderRecord] = []
        self._targets_by_provider: dict[str, list[ProviderTarget]] = {}
        self._enabled_by_provider: dict[str, bool] = {}
        self._selected_by_provider: dict[str, set[str]] = {}
        self._load_thread: Thread | None = None
        self._refresh_thread: Thread | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="source-shell"):
            yield Static("Manage Sources", id="source-header")
            yield Static("Loading providers and targets...", id="source-status")
            yield Static("Loading sources...", id="source-loading")
            yield Static("", id="source-error")
            with Horizontal(id="source-content"):
                yield DataTable(id="provider-list", classes="source-table", cursor_type="row")
                yield DataTable(id="target-list", classes="source-table", cursor_type="row")
            yield Static(
                "Tab: switch pane   Space: toggle   R: refresh catalog   A: apply   Esc: close",
                id="source-hint",
            )

    def on_mount(self) -> None:
        self.query_one("#source-error", Static).display = False
        content = self.query_one("#source-content", Horizontal)
        content.display = False
        for selector in ("#provider-list", "#target-list"):
            table = self.query_one(selector, DataTable)
            table.zebra_stripes = False
            table.show_header = False
            table.show_row_labels = False
            table.show_cursor = True
        self._load_thread = Thread(target=self._load_sources, name="newsr-sources", daemon=True)
        self._load_thread.start()

    def action_close_overlay(self) -> None:
        self.dismiss()

    def action_switch_pane(self) -> None:
        if not self._providers:
            return
        provider_table = self.query_one("#provider-list", DataTable)
        target_table = self.query_one("#target-list", DataTable)
        if provider_table.has_focus:
            target_table.focus()
        else:
            provider_table.focus()

    def action_toggle_item(self) -> None:
        if not self._providers:
            self._set_status("Sources are still loading.")
            return
        provider_table = self.query_one("#provider-list", DataTable)
        if provider_table.has_focus:
            provider = self._current_provider()
            if provider is None:
                return
            self._enabled_by_provider[provider.provider_id] = not self._enabled_by_provider[provider.provider_id]
            self._refresh_provider_rows()
            return
        target_table = self.query_one("#target-list", DataTable)
        provider = self._current_provider()
        if provider is None or not target_table.is_valid_row_index(target_table.cursor_row):
            return
        targets = self._targets_by_provider.get(provider.provider_id, [])
        target = targets[target_table.cursor_row]
        selected = self._selected_by_provider.setdefault(provider.provider_id, set())
        if target.target_key in selected:
            selected.remove(target.target_key)
        else:
            selected.add(target.target_key)
        self._refresh_target_rows(provider.provider_id)

    def action_refresh_catalog(self) -> None:
        provider = self._current_provider()
        if provider is None or self._refresh_thread is not None:
            return
        self._set_status(f"Refreshing {provider.display_name} catalog...")
        self._refresh_thread = Thread(
            target=self._refresh_provider_catalog,
            args=(provider.provider_id,),
            name="newsr-source-refresh",
            daemon=True,
        )
        self._refresh_thread.start()

    def action_save_selection(self) -> None:
        if not self._providers:
            self._set_status("Sources are still loading.")
            return
        enabled = dict(self._enabled_by_provider)
        selected = {
            provider_id: sorted(values)
            for provider_id, values in self._selected_by_provider.items()
        }
        if self.app.apply_source_configuration(enabled, selected):
            self.dismiss()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "provider-list":
            provider = self._provider_at_row(event.cursor_row)
            if provider is None:
                return
            self._refresh_target_rows(provider.provider_id)
        self._update_status_counts()

    def _load_sources(self) -> None:
        try:
            providers = self.app.list_source_providers()
            if not providers:
                raise ValueError("No providers are registered")
            targets_by_provider: dict[str, list[ProviderTarget]] = {}
            for provider in providers:
                targets = self.app.list_source_targets(provider.provider_id)
                if not targets:
                    targets = self.app.refresh_source_catalog(provider.provider_id)
                targets_by_provider[provider.provider_id] = targets
        except Exception as exc:
            if self.app.is_running:
                self.app.call_from_thread(self._show_error, f"Failed to load sources: {exc}")
            return
        if self.app.is_running:
            self.app.call_from_thread(self._show_sources, providers, targets_by_provider)

    def _refresh_provider_catalog(self, provider_id: str) -> None:
        try:
            targets = self.app.refresh_source_catalog(provider_id)
        except Exception as exc:
            if self.app.is_running:
                self.app.call_from_thread(self._show_error, f"Failed to refresh sources: {exc}")
                self.app.call_from_thread(self._clear_refresh_thread)
            return
        if self.app.is_running:
            self.app.call_from_thread(self._apply_refreshed_targets, provider_id, targets)

    def _apply_refreshed_targets(self, provider_id: str, targets: list[ProviderTarget]) -> None:
        self._targets_by_provider[provider_id] = targets
        self._selected_by_provider[provider_id] = {
            target.target_key for target in targets if target.selected
        }
        if self._current_provider_id() == provider_id:
            self._refresh_target_rows(provider_id)
        provider = next(
            (provider for provider in self._providers if provider.provider_id == provider_id),
            None,
        )
        if provider is not None:
            self._set_status(f"Refreshed {provider.display_name} catalog.")
        self._clear_refresh_thread()

    def _clear_refresh_thread(self) -> None:
        self._refresh_thread = None

    def _show_sources(
        self,
        providers: list[ProviderRecord],
        targets_by_provider: dict[str, list[ProviderTarget]],
    ) -> None:
        self._providers = providers
        self._targets_by_provider = targets_by_provider
        self._enabled_by_provider = {
            provider.provider_id: provider.enabled for provider in providers
        }
        self._selected_by_provider = {
            provider_id: {target.target_key for target in targets if target.selected}
            for provider_id, targets in targets_by_provider.items()
        }
        self.query_one("#source-loading", Static).display = False
        self.query_one("#source-error", Static).display = False
        self.query_one("#source-content", Horizontal).display = True
        self._refresh_provider_rows()
        current_provider_id = self._current_provider_id()
        if current_provider_id is not None:
            self._refresh_target_rows(current_provider_id)
        self.query_one("#provider-list", DataTable).focus()
        self._update_status_counts()

    def _show_error(self, message: str) -> None:
        self.query_one("#source-loading", Static).display = False
        self.query_one("#source-content", Horizontal).display = False
        error = self.query_one("#source-error", Static)
        error.update(message)
        error.display = True
        self._set_status("Unable to load sources.")

    def _set_status(self, message: str) -> None:
        self.query_one("#source-status", Static).update(message)

    def _refresh_provider_rows(self) -> None:
        table = self.query_one("#provider-list", DataTable)
        current_provider_id = self._current_provider_id()
        table.clear(columns=True)
        table.add_column(" ", width=3, key="marker")
        table.add_column("Provider", key="provider", width=max(16, self.size.width // 3))
        table.add_column("Targets", key="targets", width=10)
        for provider in self._providers:
            enabled = self._enabled_by_provider.get(provider.provider_id, provider.enabled)
            selected_count = len(self._selected_by_provider.get(provider.provider_id, set()))
            table.add_row(
                Text("[x]" if enabled else "[ ]"),
                provider.display_name,
                str(selected_count),
                key=provider.provider_id,
            )
        self._move_provider_cursor(current_provider_id)

    def _refresh_target_rows(self, provider_id: str) -> None:
        table = self.query_one("#target-list", DataTable)
        previous_target_key = self._current_target_key(provider_id)
        table.clear(columns=True)
        marker_width = 3
        marker_render_width = marker_width + (2 * table.cell_padding)
        target_width = max(16, table.size.width - marker_render_width - (2 * table.cell_padding))
        table.add_column(" ", width=marker_width, key="marker")
        table.add_column("Target", key="target", width=target_width)
        selected_keys = self._selected_by_provider.get(provider_id, set())
        for target in self._targets_by_provider.get(provider_id, []):
            table.add_row(
                Text("[x]" if target.target_key in selected_keys else "[ ]"),
                target.label,
                key=target.target_key,
            )
        cursor_row = 0
        if previous_target_key is not None:
            for index, target in enumerate(self._targets_by_provider.get(provider_id, [])):
                if target.target_key == previous_target_key:
                    cursor_row = index
                    break
        if table.row_count:
            table.move_cursor(row=cursor_row, column=0, animate=False, scroll=True)
        self._update_status_counts()

    def _move_provider_cursor(self, provider_id: str | None) -> None:
        table = self.query_one("#provider-list", DataTable)
        cursor_row = 0
        if provider_id is not None:
            for index, provider in enumerate(self._providers):
                if provider.provider_id == provider_id:
                    cursor_row = index
                    break
        if table.row_count:
            table.move_cursor(row=cursor_row, column=0, animate=False, scroll=True)

    def _update_status_counts(self) -> None:
        enabled_count = sum(1 for enabled in self._enabled_by_provider.values() if enabled)
        current_provider = self._current_provider()
        target_count = 0
        if current_provider is not None:
            target_count = len(self._selected_by_provider.get(current_provider.provider_id, set()))
        self._set_status(
            f"Loaded {len(self._providers)} providers. Enabled {enabled_count}. Selected {target_count} targets."
        )

    def _current_provider(self) -> ProviderRecord | None:
        table = self.query_one("#provider-list", DataTable)
        return self._provider_at_row(table.cursor_row)

    def _provider_at_row(self, row_index: int) -> ProviderRecord | None:
        if not self._providers or row_index < 0 or row_index >= len(self._providers):
            return None
        return self._providers[row_index]

    def _current_provider_id(self) -> str | None:
        provider = self._current_provider()
        return provider.provider_id if provider is not None else None

    def _current_target_key(self, provider_id: str) -> str | None:
        table = self.query_one("#target-list", DataTable)
        targets = self._targets_by_provider.get(provider_id, [])
        if not targets or not table.is_valid_row_index(table.cursor_row):
            return None
        return targets[table.cursor_row].target_key
