from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ScreenStackError
from textual.css.query import NoMatches
from textual.containers import Vertical
from textual.widgets import DataTable

from ...domain import ProviderRecord, ProviderTarget
from ..group_headers import framed_group_header_text
from ..provider_groups import build_provider_groups, provider_group_id_for_type, provider_group_label
from ..screens import ProviderHomeRow

if TYPE_CHECKING:
    from ..app import NewsReaderApp

ALL_PROVIDERS_SCOPE_ID = "[ALL]"


class ProviderHomeController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._open = False
        self._active_scope_id = ALL_PROVIDERS_SCOPE_ID
        self._selected_scope_id = ALL_PROVIDERS_SCOPE_ID
        self._last_highlighted_row = 0

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def active_scope_id(self) -> str:
        return self._active_scope_id

    @property
    def selected_scope_id(self) -> str:
        return self._selected_scope_id

    @selected_scope_id.setter
    def selected_scope_id(self, value: str) -> None:
        self._selected_scope_id = value

    def bootstrap(self) -> None:
        provider_records = [
            ProviderRecord(
                provider_id=provider.provider_id,
                display_name=provider.display_name,
                enabled=(provider.provider_id == "bbc"),
                provider_type="http",
            )
            for provider in self._app.builtin_providers.values()
        ]
        self._app.storage.sync_providers(provider_records)
        for provider in self._app.builtin_providers.values():
            if self._app.storage.list_provider_targets(provider.provider_id):
                continue
            default_targets = provider.default_targets()
            self._app.storage.replace_provider_targets(provider.provider_id, default_targets)
            self._app.storage.set_selected_targets(
                provider.provider_id,
                [target.target_key for target in default_targets if target.selected],
            )

    def rows(self) -> list[ProviderHomeRow]:
        all_articles = self._app._articles_for_scope(ALL_PROVIDERS_SCOPE_ID)
        provider_rows: list[ProviderHomeRow] = []
        if self._app.config.ui.show_all:
            provider_rows.append(
                ProviderHomeRow(
                    scope_id=ALL_PROVIDERS_SCOPE_ID,
                    display_name=ALL_PROVIDERS_SCOPE_ID,
                    unread_count=self._unread_count_for_scope(ALL_PROVIDERS_SCOPE_ID, all_articles),
                    total_count=len(all_articles),
                    provider_type="all",
                )
            )
        enabled_providers = self._app.storage.list_enabled_providers()
        provider_rows.extend(
            ProviderHomeRow(
                scope_id=provider.provider_id,
                display_name=provider.display_name,
                unread_count=self._unread_count_for_scope(
                    provider.provider_id,
                    [a for a in all_articles if a.provider_id == provider.provider_id],
                ),
                total_count=sum(1 for a in all_articles if a.provider_id == provider.provider_id),
                provider_type=provider.provider_type,
            )
            for provider in enabled_providers
        )
        result: list[ProviderHomeRow] = []
        for group in build_provider_groups(
            provider_rows,
            group_for_item=lambda row: provider_group_id_for_type(row.provider_type),
            sort_items=self._sort_rows,
        ):
            result.append(
                ProviderHomeRow(
                    scope_id=None,
                    display_name=provider_group_label(self._app.ui, group.group_id),
                    unread_count=0,
                    total_count=0,
                    is_group_header=True,
                )
            )
            result.extend(group.items)
        return result

    def _sort_rows(self, rows: list[ProviderHomeRow]) -> list[ProviderHomeRow]:
        primary = self._app.config.ui.provider_sort.primary
        direction = self._app.config.ui.provider_sort.direction
        if primary == "name":
            return sorted(
                rows,
                key=lambda row: row.display_name.casefold(),
                reverse=direction == "desc",
            )
        reverse = direction == "desc"
        return sorted(
            rows,
            key=lambda row: (
                -row.unread_count if reverse else row.unread_count,
                row.display_name.casefold(),
            ),
        )

    def _unread_count_for_scope(self, scope_id: str, articles: list) -> int:
        if not articles:
            return 0
        state = self._app.storage.load_reader_state(scope_id)
        if state.article_id is None:
            return len(articles)
        for index, article in enumerate(articles):
            if article.article_id == state.article_id:
                return max(0, len(articles) - index - 1)
        return len(articles)

    def show(self) -> None:
        self._selected_scope_id = self._active_scope_id
        self._open = True
        self.refresh_rows()
        self._notify_bindings_changed()
        self._app.refresh_view()
        try:
            table = self._app.query_one("#provider-home-table", DataTable)
        except NoMatches:
            return
        table.focus()
        self._restore_cursor_for_scope(table, self._selected_scope_id)

    def close(self) -> None:
        self._open = False
        self._notify_bindings_changed()
        self._app.refresh_view()

    def open_scope(self, scope_id: str) -> None:
        self._activate_scope(scope_id, close_provider_home=True)

    def show_home_for_unavailable_scope(self) -> None:
        self._app._persist_reader_state()
        self.show()

    def handle_deleted_provider(self, provider_id: str) -> None:
        if self._active_scope_id == provider_id:
            self.show_home_for_unavailable_scope()
        if self._open:
            self.refresh_rows()

    def _activate_scope(self, scope_id: str, *, close_provider_home: bool) -> None:
        self._app._persist_reader_state()
        self._active_scope_id = scope_id
        self._selected_scope_id = scope_id
        self._app.reader_state = self._app.storage.load_reader_state(scope_id)
        self._app._navigation._state_persisted = False
        self._app.load_articles(
            preferred_article_id=self._app.reader_state.article_id,
            fallback_to_current_article=False,
        )
        self._app._navigation.queue_scroll_restore()
        if close_provider_home:
            self.close()
        self._app.refresh_view()

    def open_selected_scope(self) -> None:
        try:
            table = self._app.query_one("#provider-home-table", DataTable)
        except NoMatches:
            return
        home_rows = self.rows()
        row = self._row_at(home_rows, table.cursor_row)
        if row is None:
            return
        self.open_scope(row.scope_id)

    def refresh_rows(self) -> None:
        if not self._app.is_mounted:
            return
        table = self._app.query_one("#provider-home-table", DataTable)
        home_rows = self.rows()
        previous_scope_id = self._selected_scope_id
        table.clear(columns=True)
        provider_width = self._provider_width(table)
        counter_width = 6
        counter_text_width = max(1, counter_width - (2 * table.cell_padding))
        table.add_column(self._app.ui.text("provider_home.table.provider"), key="provider", width=provider_width)
        table.add_column(self._app.ui.text("provider_home.table.unread"), key="unread", width=counter_width)
        table.add_column(self._app.ui.text("provider_home.table.total"), key="total", width=counter_width)
        selected_row = self._selected_row_index(home_rows, previous_scope_id)
        for index, row in enumerate(home_rows):
            table.add_row(
                self._provider_cell(row, provider_width=provider_width),
                "" if row.is_group_header else f"{row.unread_count:>{counter_text_width}}",
                "" if row.is_group_header else f"{row.total_count:>{counter_text_width}}",
                key=row.scope_id or f"group:{row.display_name}",
            )
        if selected_row is not None:
            self._selected_scope_id = home_rows[selected_row].scope_id
            self._last_highlighted_row = selected_row
            table.move_cursor(row=selected_row, column=0, animate=False, scroll=True)
        self._app._navigation._rendered_article_url = None

    def _provider_width(self, table: DataTable) -> int:
        available_width = table.size.width
        if available_width <= 0:
            try:
                available_width = self._app.query_one("#article-frame", Vertical).size.width
            except NoMatches:
                available_width = self._app.size.width
        if available_width <= 0:
            available_width = self._app.size.width
        table_padding = 2 * table.cell_padding
        counter_width = 6
        reserved = (counter_width * 2) + (table_padding * 3) + 6
        return max(12, available_width - reserved)

    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "provider-home-table":
            return
        home_rows = self.rows()
        row = self._row_at(home_rows, event.cursor_row)
        if row is None:
            return
        self.open_scope(row.scope_id)

    def handle_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "provider-home-table":
            return
        home_rows = self.rows()
        if event.cursor_row < 0 or event.cursor_row >= len(home_rows):
            return
        row = home_rows[event.cursor_row]
        if row.scope_id is None:
            direction = -1 if event.cursor_row < self._last_highlighted_row else 1
            target_row = self._adjacent_selectable_row(
                home_rows,
                event.cursor_row,
                step=direction,
            )
            if target_row is None:
                target_row = self._selected_row_index(home_rows, self._selected_scope_id)
            if target_row is None:
                target_row = self._adjacent_selectable_row(home_rows, event.cursor_row, step=-direction)
            if target_row is not None:
                event.data_table.move_cursor(row=target_row, column=0, animate=False, scroll=True)
            return
        self._last_highlighted_row = event.cursor_row
        self._selected_scope_id = row.scope_id
        self._app.refresh_view()

    def check_action(self, action: str) -> bool | None:
        if not self._open:
            return True
        provider_home_actions = {
            "scroll_up",
            "scroll_down",
            "page_up",
            "page_down",
            "show_source_manager",
            "watch_topic",
            "download_articles",
            "show_help",
            "quit_reader",
            "command_palette",
        }
        hidden_in_provider_home = {
            "previous_article",
            "next_article",
            "classify_article_categories",
            "toggle_summary",
            "show_or_refresh_more_info",
            "show_article_qa",
            "show_quick_nav",
            "export_current",
            "open_article",
            "return_to_provider_home",
        }
        if action in provider_home_actions:
            return True
        if action in hidden_in_provider_home:
            return False
        return True

    def _notify_bindings_changed(self) -> None:
        try:
            screen = self._app.screen
        except ScreenStackError:
            return
        try:
            screen.bindings_updated_signal.publish(screen)
        except ScreenStackError:
            pass

    def move_cursor(self, delta: int) -> None:
        try:
            table = self._app.query_one("#provider-home-table", DataTable)
        except NoMatches:
            return
        if delta == 0:
            return
        home_rows = self.rows()
        current = table.cursor_row
        step = 1 if delta > 0 else -1
        for _ in range(abs(delta)):
            next_row = self._adjacent_selectable_row(home_rows, current + step, step=step)
            if next_row is None:
                break
            current = next_row
        if current != table.cursor_row:
            table.move_cursor(row=current, column=0, animate=False, scroll=True)

    def page_cursor(self, step: int) -> None:
        try:
            table = self._app.query_one("#provider-home-table", DataTable)
        except NoMatches:
            return
        if step == 0 or not table.show_cursor or table.cursor_type not in ("cell", "row"):
            return
        page_height = table.scrollable_content_region.height - (
            table.header_height if table.show_header else 0
        )
        if page_height <= 0:
            return
        row_index = table.cursor_row
        rows_to_scroll = self._page_row_count(table, row_index, step=step, page_height=page_height)
        if rows_to_scroll <= 0:
            return
        target_row = row_index + rows_to_scroll - 1 if step > 0 else row_index - rows_to_scroll + 1
        selectable_row = self._page_selectable_row(self.rows(), target_row, step=1 if step > 0 else -1)
        if selectable_row is None or selectable_row == table.cursor_row:
            return
        if step > 0:
            table.scroll_relative(y=page_height, animate=False, force=True)
        else:
            table.scroll_relative(y=-page_height, animate=False)
        table.move_cursor(row=selectable_row, column=0, animate=False, scroll=False)

    def move_to_boundary(self, *, first: bool) -> None:
        try:
            table = self._app.query_one("#provider-home-table", DataTable)
        except NoMatches:
            return
        target_row = self._boundary_selectable_row(self.rows(), first=first)
        if target_row is None or target_row == table.cursor_row:
            return
        table.move_cursor(row=target_row, column=0, animate=False, scroll=True)

    def list_providers(self) -> list[ProviderRecord]:
        return self._app.storage.list_providers()

    def list_targets(self, provider_id: str) -> list[ProviderTarget]:
        return self._app.storage.list_provider_targets(provider_id)

    def refresh_catalog(self, provider_id: str) -> list[ProviderTarget]:
        provider = self._app.providers[provider_id]
        provider_record = self._app.storage.get_provider(provider_id)
        if provider_record is not None and provider_record.provider_type == "topic":
            return self._app.storage.list_provider_targets(provider_id)
        current_selected = {
            target.target_key for target in self._app.storage.list_selected_targets(provider_id)
        }
        targets = provider.discover_targets()
        self._app.storage.replace_provider_targets(provider_id, targets)
        selected_keys = [target.target_key for target in targets if target.target_key in current_selected]
        if not selected_keys:
            selected_keys = [target.target_key for target in targets if target.selected]
        self._app.storage.set_selected_targets(provider_id, selected_keys)
        return self._app.storage.list_provider_targets(provider_id)

    def apply_configuration(
        self,
        enabled_by_provider: dict[str, bool],
        selected_targets: dict[str, list[str]],
    ) -> bool:
        current_enabled = {
            provider.provider_id: provider.enabled for provider in self._app.storage.list_providers()
        }
        current_selected = {
            provider.provider_id: sorted(
                target.target_key for target in self._app.storage.list_selected_targets(provider.provider_id)
            )
            for provider in self._app.storage.list_providers()
        }
        if enabled_by_provider == current_enabled and selected_targets == current_selected:
            self._app._refresh.set_status_text(self._app.ui.text("app.status.sources_unchanged"), busy=False)
            self._app.refresh_view()
            return True
        for provider_id, enabled in enabled_by_provider.items():
            self._app.storage.set_provider_enabled(provider_id, enabled)
        for provider_id, target_keys in selected_targets.items():
            self._app.storage.set_selected_targets(provider_id, target_keys)
        self._app._refresh.request_due_refresh_check()
        if (
            self._active_scope_id != ALL_PROVIDERS_SCOPE_ID
            and not enabled_by_provider.get(self._active_scope_id, False)
        ):
            self.show_home_for_unavailable_scope()
        if self._open:
            self.refresh_rows()
        self._app._refresh.set_status_text(self._app.ui.text("app.status.sources_saved"), busy=False)
        self._app.refresh_view()
        return True

    @staticmethod
    def _provider_cell(row: ProviderHomeRow, *, provider_width: int) -> Text | str:
        if row.is_group_header:
            return framed_group_header_text(row.display_name, provider_width)
        return row.display_name

    @staticmethod
    def _row_at(rows: list[ProviderHomeRow], index: int) -> ProviderHomeRow | None:
        if index < 0 or index >= len(rows):
            return None
        row = rows[index]
        if row.scope_id is None:
            return None
        return row

    def _selected_row_index(self, rows: list[ProviderHomeRow], scope_id: str) -> int | None:
        for index, row in enumerate(rows):
            if row.scope_id == scope_id:
                return index
        return self._adjacent_selectable_row(rows, 0, step=1)

    def _restore_cursor_for_scope(self, table: DataTable, scope_id: str) -> None:
        row_index = self._selected_row_index(self.rows(), scope_id)
        if row_index is None:
            return
        self._last_highlighted_row = row_index
        table.move_cursor(row=row_index, column=0, animate=False, scroll=True)

    @staticmethod
    def _boundary_selectable_row(rows: list[ProviderHomeRow], *, first: bool) -> int | None:
        start = 0 if first else len(rows) - 1
        step = 1 if first else -1
        return ProviderHomeController._adjacent_selectable_row(rows, start, step=step)

    @staticmethod
    def _page_selectable_row(rows: list[ProviderHomeRow], target_row: int, *, step: int) -> int | None:
        selectable_row = ProviderHomeController._adjacent_selectable_row(rows, target_row, step=step)
        if selectable_row is not None:
            return selectable_row
        selectable_row = ProviderHomeController._boundary_selectable_row(rows, first=step < 0)
        if selectable_row is not None:
            return selectable_row
        return ProviderHomeController._adjacent_selectable_row(rows, target_row, step=-step)

    @staticmethod
    def _page_row_count(table: DataTable, row_index: int, *, step: int, page_height: int) -> int:
        offset = 0
        rows_to_scroll = 0
        ordered_rows = table.ordered_rows[row_index:] if step > 0 else table.ordered_rows[: row_index + 1]
        for ordered_row in ordered_rows:
            offset += ordered_row.height
            rows_to_scroll += 1
            if offset > page_height:
                break
        return rows_to_scroll

    @staticmethod
    def _adjacent_selectable_row(rows: list[ProviderHomeRow], start: int, *, step: int) -> int | None:
        index = start
        while 0 <= index < len(rows):
            if rows[index].scope_id is not None:
                return index
            index += step
        return None
