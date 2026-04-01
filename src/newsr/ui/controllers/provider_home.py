from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ScreenStackError
from textual.css.query import NoMatches
from textual.containers import Vertical
from textual.widgets import DataTable

from ...domain import ProviderRecord, ProviderTarget
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
            )
            for provider in self._app.providers.values()
        ]
        self._app.storage.sync_providers(provider_records)
        for provider in self._app.providers.values():
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
        result: list[ProviderHomeRow] = []
        if self._app.config.ui.show_all:
            result.append(
                ProviderHomeRow(
                    scope_id=ALL_PROVIDERS_SCOPE_ID,
                    display_name=ALL_PROVIDERS_SCOPE_ID,
                    unread_count=self._unread_count_for_scope(ALL_PROVIDERS_SCOPE_ID, all_articles),
                    total_count=len(all_articles),
                )
            )
        enabled_providers = self._app.storage.list_enabled_providers()
        provider_rows = [
            ProviderHomeRow(
                scope_id=provider.provider_id,
                display_name=provider.display_name,
                unread_count=self._unread_count_for_scope(
                    provider.provider_id,
                    [a for a in all_articles if a.provider_id == provider.provider_id],
                ),
                total_count=sum(1 for a in all_articles if a.provider_id == provider.provider_id),
            )
            for provider in enabled_providers
        ]
        result.extend(self._sort_rows(provider_rows))
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
            self._app.query_one("#provider-home-table", DataTable).focus()
        except NoMatches:
            pass

    def close(self) -> None:
        self._open = False
        self._notify_bindings_changed()
        self._app.refresh_view()

    def open_scope(self, scope_id: str) -> None:
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
        self.close()
        self._app.refresh_view()
        self._app._navigation.maybe_auto_fetch()

    def open_selected_scope(self) -> None:
        try:
            table = self._app.query_one("#provider-home-table", DataTable)
        except NoMatches:
            return
        home_rows = self.rows()
        if table.cursor_row < 0 or table.cursor_row >= len(home_rows):
            return
        self.open_scope(home_rows[table.cursor_row].scope_id)

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
        selected_row = 0
        for index, row in enumerate(home_rows):
            table.add_row(
                row.display_name,
                f"{row.unread_count:>{counter_text_width}}",
                f"{row.total_count:>{counter_text_width}}",
                key=row.scope_id,
            )
            if row.scope_id == previous_scope_id:
                selected_row = index
        if home_rows:
            self._selected_scope_id = home_rows[selected_row].scope_id
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
        if event.cursor_row < 0 or event.cursor_row >= len(home_rows):
            return
        self.open_scope(home_rows[event.cursor_row].scope_id)

    def handle_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "provider-home-table":
            return
        home_rows = self.rows()
        if event.cursor_row < 0 or event.cursor_row >= len(home_rows):
            return
        self._selected_scope_id = home_rows[event.cursor_row].scope_id
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
        current = table.cursor_row
        new_row = max(0, min(table.row_count - 1, current + delta))
        if new_row != current:
            table.move_cursor(row=new_row, column=0, animate=False, scroll=True)

    def list_providers(self) -> list[ProviderRecord]:
        return self._app.storage.list_providers()

    def list_targets(self, provider_id: str) -> list[ProviderTarget]:
        return self._app.storage.list_provider_targets(provider_id)

    def refresh_catalog(self, provider_id: str) -> list[ProviderTarget]:
        provider = self._app.providers[provider_id]
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
        if (
            self._active_scope_id != ALL_PROVIDERS_SCOPE_ID
            and not enabled_by_provider.get(self._active_scope_id, False)
        ):
            self.open_scope(ALL_PROVIDERS_SCOPE_ID)
        if self._open:
            self.refresh_rows()
        if self._app._refresh.in_progress:
            self._app._refresh.set_status_text(
                self._app.ui.text("app.status.sources_saved_next_refresh"),
                busy=False,
            )
            self._app.refresh_view()
            return True
        self._app._refresh.set_status_text(self._app.ui.text("app.status.sources_saved_refreshing"), busy=False)
        self._app.refresh_view()
        self._app._refresh.start()
        return True
