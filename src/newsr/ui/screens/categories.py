from __future__ import annotations

from dataclasses import dataclass
from threading import Thread

from rich.cells import cell_len
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

from ...domain import ProviderRecord, ProviderTarget
from ...scheduling import validate_cron_expression
from ...ui_text import UILocalizer
from ..group_headers import group_header_text
from ..provider_groups import build_provider_groups, provider_group_id_for_type, provider_group_label
from .confirm_dialog import ConfirmDialogScreen
from .text_input_dialog import TextInputDialogScreen


@dataclass(slots=True)
class SourceProviderRow:
    label: str
    provider: ProviderRecord | None = None
    is_group_header: bool = False


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
    #target-list {
        padding-top: 1;
    }
    #source-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    """

    BINDINGS = []

    def __init__(self, ui: UILocalizer, *, default_schedule: str) -> None:
        super().__init__()
        self._ui = ui
        self._default_schedule = default_schedule
        self._bindings = BindingsMap(self._build_bindings())
        self._providers: list[ProviderRecord] = []
        self._targets_by_provider: dict[str, list[ProviderTarget]] = {}
        self._enabled_by_provider: dict[str, bool] = {}
        self._selected_by_provider: dict[str, set[str]] = {}
        self._provider_rows: list[SourceProviderRow] = []
        self._selected_provider_id: str | None = None
        self._target_provider_id: str | None = None
        self._load_thread: Thread | None = None
        self._refresh_thread: Thread | None = None
        self._last_provider_row_index = 0
        self._last_focused_table_id = "provider-list"

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            Binding("escape", "close_overlay", self._ui.text("source.binding.close"), show=False),
            Binding("tab", "switch_pane", self._ui.text("source.binding.pane"), show=False),
            Binding("space", "toggle_item", self._ui.text("source.binding.toggle"), show=False),
            Binding("r", "refresh_catalog", self._ui.text("source.binding.refresh"), show=False),
            ("u", "edit_schedule", self._ui.text("source.binding.schedule")),
            ("x", "delete_provider", self._ui.text("source.binding.delete")),
            ("a", "save_selection", self._ui.text("source.binding.apply")),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="source-shell"):
            yield Static(self._ui.text("source.header"), id="source-header")
            yield Static(self._ui.text("source.loading.status"), id="source-status")
            yield Static(self._ui.text("source.loading.body"), id="source-loading")
            yield Static("", id="source-error")
            with Horizontal(id="source-content"):
                yield DataTable(id="provider-list", classes="source-table", cursor_type="row")
                yield DataTable(id="target-list", classes="source-table", cursor_type="row")
            yield Static(self._ui.text("source.hint"), id="source-hint")

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

    def on_resize(self, event: Resize) -> None:
        if not self._providers:
            return
        current_provider_id = self._current_provider_id()
        self._refresh_provider_rows(current_provider_id)
        current_provider_id = self._current_provider_id()
        if current_provider_id is not None:
            self._refresh_target_rows(current_provider_id)

    def action_close_overlay(self) -> None:
        self.dismiss()
        self.app.restore_navigation_focus()

    def action_switch_pane(self) -> None:
        if not self._providers:
            return
        provider_table = self.query_one("#provider-list", DataTable)
        target_table = self.query_one("#target-list", DataTable)
        if provider_table.has_focus:
            target_table.focus()
            self._last_focused_table_id = "target-list"
        else:
            provider_table.focus()
            self._last_focused_table_id = "provider-list"

    def action_toggle_item(self) -> None:
        if not self._providers:
            self._set_status(self._ui.text("source.status.still_loading"))
            return
        provider_table = self.query_one("#provider-list", DataTable)
        if provider_table.has_focus:
            provider = self._current_provider()
            if provider is None:
                return
            self._enabled_by_provider[provider.provider_id] = not self._enabled_by_provider[provider.provider_id]
            self._update_provider_row(provider.provider_id)
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
        self._set_status(self._ui.text("source.status.refreshing_catalog", provider=provider.display_name))
        self._refresh_thread = Thread(
            target=self._refresh_provider_catalog,
            args=(provider.provider_id,),
            name="newsr-source-refresh",
            daemon=True,
        )
        self._refresh_thread.start()

    def action_save_selection(self) -> None:
        if not self._providers:
            self._set_status(self._ui.text("source.status.still_loading"))
            return
        enabled = dict(self._enabled_by_provider)
        selected = {
            provider_id: sorted(values)
            for provider_id, values in self._selected_by_provider.items()
        }
        if self.app.apply_source_configuration(enabled, selected):
            self.dismiss()
            self.app.restore_navigation_focus()

    def action_edit_schedule(self) -> None:
        provider = self._current_provider()
        if provider is None:
            return
        self.app.push_screen(
            TextInputDialogScreen(
                self._ui,
                title=self._ui.text("source.schedule.title", provider=provider.display_name),
                body=self._ui.text("source.schedule.body", default_schedule=self._default_schedule),
                initial_value=provider.update_schedule or "",
                placeholder=self._ui.text(
                    "source.schedule.placeholder",
                    default_schedule=self._default_schedule,
                ),
                confirm_label=self._ui.text("source.schedule.confirm"),
                cancel_label=self._ui.text("source.schedule.cancel"),
                validator=self._validate_schedule,
            ),
            callback=lambda result: self._apply_schedule_result(provider.provider_id, result),
        )

    def action_delete_provider(self) -> None:
        provider = self._current_provider()
        if provider is None or provider.provider_type != "topic":
            return
        self.app.push_screen(
            ConfirmDialogScreen(
                self._ui,
                title=self._ui.text("source.delete.title"),
                body=self._ui.text("source.delete.body", provider=provider.display_name),
                confirm_label=self._ui.text("source.delete.confirm"),
                cancel_label=self._ui.text("source.delete.cancel"),
            ),
            callback=lambda confirmed: self._delete_provider(provider.provider_id) if confirmed else None,
        )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "provider-list":
            row = self._provider_row_at(event.cursor_row)
            if row is not None and row.is_group_header:
                target_row = self._adjacent_provider_row(
                    event.cursor_row,
                    step=-1 if event.cursor_row < self._last_provider_row_index else 1,
                )
                if target_row is None:
                    target_row = self._adjacent_provider_row(
                        event.cursor_row,
                        step=1 if event.cursor_row < self._last_provider_row_index else -1,
                    )
                if target_row is not None:
                    event.data_table.move_cursor(row=target_row, column=0, animate=False, scroll=True)
                return
            provider = row.provider if row is not None else None
            if provider is None:
                return
            self._last_provider_row_index = event.cursor_row
            self._selected_provider_id = provider.provider_id
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
                self.app.call_from_thread(self._show_error, self._ui.text("source.status.failed_load", error=exc))
            return
        if self.app.is_running:
            self.app.call_from_thread(self._show_sources, providers, targets_by_provider)

    def _refresh_provider_catalog(self, provider_id: str) -> None:
        try:
            targets = self.app.refresh_source_catalog(provider_id)
        except Exception as exc:
            if self.app.is_running:
                self.app.call_from_thread(self._show_error, self._ui.text("source.status.failed_refresh", error=exc))
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
            self._set_status(self._ui.text("source.status.refreshed_catalog", provider=provider.display_name))
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
        self.call_after_refresh(self._show_sources_after_layout)

    def _show_sources_after_layout(self) -> None:
        self._refresh_provider_rows()
        current_provider_id = self._current_provider_id()
        if current_provider_id is not None:
            self._refresh_target_rows(current_provider_id)
        self.query_one("#provider-list", DataTable).focus()
        self._last_focused_table_id = "provider-list"
        self._update_status_counts()

    def restore_navigation_focus(self) -> None:
        table_id = self._last_focused_table_id
        try:
            table = self.query_one(f"#{table_id}", DataTable)
        except NoMatches:
            table = self.query_one("#provider-list", DataTable)
        table.focus()

    def _show_error(self, message: str) -> None:
        self.query_one("#source-loading", Static).display = False
        self.query_one("#source-content", Horizontal).display = False
        error = self.query_one("#source-error", Static)
        error.update(message)
        error.display = True
        self._set_status(self._ui.text("source.status.unable_to_load"))

    def _set_status(self, message: str) -> None:
        self.query_one("#source-status", Static).update(message)

    def _refresh_provider_rows(self, preferred_provider_id: str | None = None) -> None:
        table = self.query_one("#provider-list", DataTable)
        current_provider_id = preferred_provider_id or self._selected_provider_id or self._current_provider_id()
        self._provider_rows = self._build_provider_rows()
        table.clear(columns=True)
        marker_width, provider_width, type_width, schedule_width = self._provider_column_widths(table)
        table.add_column(" ", width=marker_width, key="marker")
        table.add_column(self._ui.text("source.table.provider"), key="provider", width=provider_width)
        table.add_column(self._ui.text("source.table.type"), key="type", width=type_width)
        table.add_column(self._ui.text("source.table.schedule"), key="schedule", width=schedule_width)
        for row in self._provider_rows:
            if row.is_group_header:
                table.add_row("", group_header_text(row.label), "", "", key=f"group:{row.label}")
                continue
            provider = row.provider
            assert provider is not None
            enabled = self._enabled_by_provider.get(provider.provider_id, provider.enabled)
            table.add_row(
                Text("[x]" if enabled else "[ ]"),
                provider.display_name,
                self._provider_type_label(provider.provider_type),
                provider.update_schedule or self._ui.text("source.schedule.default"),
                key=provider.provider_id,
            )
        self.call_after_refresh(lambda: self._move_provider_cursor(current_provider_id))

    def _update_provider_row(self, provider_id: str) -> None:
        if not self.is_mounted:
            return
        provider = next((item for item in self._providers if item.provider_id == provider_id), None)
        row_index = self._provider_row_index(provider_id)
        if provider is None or row_index is None:
            self._refresh_provider_rows(provider_id)
            return
        table = self.query_one("#provider-list", DataTable)
        enabled = self._enabled_by_provider.get(provider.provider_id, provider.enabled)
        table.update_cell(provider.provider_id, "marker", Text("[x]" if enabled else "[ ]"))
        table.update_cell(
            provider.provider_id,
            "schedule",
            provider.update_schedule or self._ui.text("source.schedule.default"),
        )
        self._selected_provider_id = provider.provider_id
        self._last_provider_row_index = row_index
        table.move_cursor(row=row_index, column=0, animate=False, scroll=True)

    def _provider_column_widths(self, table: DataTable) -> tuple[int, int, int, int]:
        marker_width = 3
        type_width = max(cell_len(self._ui.text("source.table.type")), cell_len("topic"))
        provider_min_width = 8
        schedule_min_width = max(cell_len(self._ui.text("source.table.schedule")), 10)
        available_width = table.size.width or max(32, self.size.width // 2)
        column_count = len(table.ordered_columns) or 4
        chrome_width = (column_count * (2 * table.cell_padding)) + max(column_count - 1, 0)
        content_width = max(20, available_width - chrome_width)
        flexible_width = max(provider_min_width + schedule_min_width, content_width - marker_width - type_width)
        schedule_width = min(max(schedule_min_width, flexible_width // 2), flexible_width - provider_min_width)
        provider_width = flexible_width - schedule_width
        return marker_width, provider_width, type_width, schedule_width

    def _refresh_target_rows(self, provider_id: str) -> None:
        table = self.query_one("#target-list", DataTable)
        previous_target_key = self._current_target_key() if self._target_provider_id == provider_id else None
        table.clear(columns=True)
        marker_width = 3
        marker_render_width = marker_width + (2 * table.cell_padding)
        target_width = max(16, table.size.width - marker_render_width - (2 * table.cell_padding))
        table.add_column(" ", width=marker_width, key="marker")
        table.add_column(self._ui.text("source.table.target"), key="target", width=target_width)
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
        self._target_provider_id = provider_id
        self._update_status_counts()

    def _move_provider_cursor(self, provider_id: str | None) -> None:
        table = self.query_one("#provider-list", DataTable)
        cursor_row = self._provider_row_index(provider_id)
        if cursor_row is not None and table.row_count:
            self._last_provider_row_index = cursor_row
            row = self._provider_row_at(cursor_row)
            if row is not None and row.provider is not None:
                self._selected_provider_id = row.provider.provider_id
            table.move_cursor(row=cursor_row, column=0, animate=False, scroll=True)

    def _update_status_counts(self) -> None:
        enabled_count = sum(1 for enabled in self._enabled_by_provider.values() if enabled)
        target_count = sum(len(selected) for selected in self._selected_by_provider.values())
        self._set_status(
            self._ui.text(
                "source.status.counts",
                providers=len(self._providers),
                enabled=enabled_count,
                selected=target_count,
            )
        )

    def _provider_type_label(self, provider_type: str) -> str:
        return self._ui.text(f"source.provider_type.{provider_type}")

    def _current_provider(self) -> ProviderRecord | None:
        table = self.query_one("#provider-list", DataTable)
        row = self._provider_row_at(table.cursor_row)
        return row.provider if row is not None else None

    def _provider_row_at(self, row_index: int) -> SourceProviderRow | None:
        if not self._provider_rows or row_index < 0 or row_index >= len(self._provider_rows):
            return None
        return self._provider_rows[row_index]

    def _current_provider_id(self) -> str | None:
        provider = self._current_provider()
        return provider.provider_id if provider is not None else None

    def _current_target_key(self) -> str | None:
        if self._target_provider_id is None:
            return None
        table = self.query_one("#target-list", DataTable)
        targets = self._targets_by_provider.get(self._target_provider_id, [])
        cursor_row = table.cursor_row
        if (
            not targets
            or cursor_row < 0
            or cursor_row >= len(targets)
            or not table.is_valid_row_index(cursor_row)
        ):
            return None
        return targets[cursor_row].target_key

    def _validate_schedule(self, raw: str) -> tuple[str | None, str | None]:
        stripped = raw.strip()
        if not stripped:
            return "", None
        try:
            return validate_cron_expression(stripped), None
        except ValueError as exc:
            return None, self._ui.text("watch_topic.error.invalid_schedule", error=exc)

    def _apply_schedule_result(self, provider_id: str, result: str | None) -> None:
        if result is None:
            return
        provider = next((item for item in self._providers if item.provider_id == provider_id), None)
        if provider is None:
            return
        normalized_result = result or None
        provider.update_schedule = normalized_result
        self.app.update_provider_schedule(provider_id, normalized_result)
        self._update_provider_row(provider_id)
        self._set_status(self._ui.text("source.schedule.saved", provider=provider.display_name))

    def _delete_provider(self, provider_id: str) -> None:
        self.app.delete_topic_provider(provider_id)
        self._providers = [provider for provider in self._providers if provider.provider_id != provider_id]
        self._targets_by_provider.pop(provider_id, None)
        self._enabled_by_provider.pop(provider_id, None)
        self._selected_by_provider.pop(provider_id, None)
        if self._selected_provider_id == provider_id:
            self._selected_provider_id = None
        self._refresh_provider_rows()
        current_provider_id = self._current_provider_id()
        if current_provider_id is not None:
            self._refresh_target_rows(current_provider_id)
        else:
            self.query_one("#target-list", DataTable).clear(columns=True)
        self._set_status(self._ui.text("source.delete.deleted"))

    def _build_provider_rows(self) -> list[SourceProviderRow]:
        rows: list[SourceProviderRow] = []
        for group in build_provider_groups(
            self._providers,
            group_for_item=lambda provider: provider_group_id_for_type(provider.provider_type),
            sort_items=self._sort_providers_by_name,
            group_order=("providers", "topics"),
        ):
            rows.append(SourceProviderRow(label=provider_group_label(self._ui, group.group_id), is_group_header=True))
            rows.extend(SourceProviderRow(label=provider.display_name, provider=provider) for provider in group.items)
        return rows

    @staticmethod
    def _sort_providers_by_name(providers: list[ProviderRecord]) -> list[ProviderRecord]:
        return sorted(providers, key=lambda provider: provider.display_name.casefold())

    def _provider_row_index(self, provider_id: str | None) -> int | None:
        if provider_id is not None:
            for index, row in enumerate(self._provider_rows):
                provider = row.provider
                if provider is not None and provider.provider_id == provider_id:
                    return index
        return self._adjacent_provider_row(0, step=1)

    def _adjacent_provider_row(self, start: int, *, step: int) -> int | None:
        index = start
        while 0 <= index < len(self._provider_rows):
            if self._provider_rows[index].provider is not None:
                return index
            index += step
        return None
