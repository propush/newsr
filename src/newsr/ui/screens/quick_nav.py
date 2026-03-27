from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

from ...domain.articles import ArticleRecord


class QuickNavScreen(ModalScreen[None]):
    CSS = """
    QuickNavScreen {
        background: $background;
    }
    #quick-nav-shell {
        height: 1fr;
        border: heavy $primary;
        background: $background;
    }
    #quick-nav-header {
        height: auto;
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #quick-nav-table {
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
    #quick-nav-empty {
        height: 1fr;
        content-align: center middle;
        color: $secondary;
    }
    #quick-nav-selection {
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    #quick-nav-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    """

    BINDINGS = [
        ("escape", "close_overlay", "Close"),
    ]

    def __init__(
        self,
        articles: list[ArticleRecord],
        current_article_id: str | None,
        provider_display_names: dict[str, str],
    ) -> None:
        super().__init__()
        self._all_articles = articles
        self._current_article_id = current_article_id
        self._provider_display_names = provider_display_names
        self._visible_articles: list[ArticleRecord] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="quick-nav-shell"):
            yield Static("Quick Navigation", id="quick-nav-header")
            yield DataTable(id="quick-nav-table", cursor_type="row")
            yield Static("No translated articles available.", id="quick-nav-empty")
            yield Static(id="quick-nav-selection")
            yield Static("Up/Down: select   Enter: open article   Esc: close", id="quick-nav-hint")

    def on_mount(self) -> None:
        self._configure_table()
        self._refresh_rows()

    def on_resize(self, event: Resize) -> None:
        self._refresh_rows()

    def action_close_overlay(self) -> None:
        self.dismiss()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not self._visible_articles:
            return
        article = self._visible_articles[event.cursor_row]
        self.app.open_article_by_id(article.article_id)
        self.dismiss()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._update_selection_status(event.cursor_row)

    def _configure_table(self) -> None:
        table = self.query_one("#quick-nav-table", DataTable)
        table.zebra_stripes = True
        table.show_header = True
        table.show_cursor = True

    def _refresh_rows(self) -> None:
        table = self.query_one("#quick-nav-table", DataTable)
        empty = self.query_one("#quick-nav-empty", Static)
        previous_article_id = self._selected_article_id(table)
        self._visible_articles = [
            article
            for article in self._all_articles
            if article.translated_title is not None and article.translated_title.strip()
        ]
        title_width = self._title_column_width()
        category_width = self._category_column_width()
        table.clear(columns=True)
        table.add_column(" ", width=1, key="marker")
        table.add_column("Date", width=10, key="date")
        table.add_column("Title", width=title_width, key="title")
        table.add_column("Provider", width=self._provider_column_width(), key="provider")
        table.add_column("Category", width=category_width, key="category")
        if not self._visible_articles:
            table.display = False
            empty.display = True
            self.query_one("#quick-nav-selection", Static).update("Selected 0 of 0")
            return

        table.display = True
        empty.display = False
        for article in self._visible_articles:
            marker = ">" if article.article_id == self._current_article_id else ""
            table.add_row(
                marker,
                self._format_short_article_date(article),
                self._trimmed_title(article, title_width),
                self._provider_label(article),
                article.category,
                key=article.article_id,
            )

        selected_article_id = previous_article_id or self._current_article_id
        selected_index = 0
        if selected_article_id is not None:
            for index, article in enumerate(self._visible_articles):
                if article.article_id == selected_article_id:
                    selected_index = index
                    break
        table.move_cursor(row=selected_index, column=0, animate=False, scroll=True)
        self._update_selection_status(selected_index)
        table.focus()

    def _selected_article_id(self, table: DataTable) -> str | None:
        if not self._visible_articles or not table.is_valid_row_index(table.cursor_row):
            return None
        return self._visible_articles[table.cursor_row].article_id

    def _title_column_width(self) -> int:
        return max(12, self.size.width - self._provider_column_width() - self._category_column_width() - 20)

    @staticmethod
    def _category_column_width() -> int:
        return 16

    @staticmethod
    def _provider_column_width() -> int:
        return 16

    @staticmethod
    def _format_short_article_date(article: ArticleRecord) -> str:
        date = article.published_at or article.created_at
        return date.astimezone().strftime("%Y-%m-%d")

    @staticmethod
    def _trimmed_title(article: ArticleRecord, width: int) -> str:
        title = article.translated_title or ""
        if len(title) <= width:
            return title
        if width <= 3:
            return title[:width]
        return f"{title[: width - 3]}..."

    def _provider_label(self, article: ArticleRecord) -> str:
        provider_id = article.provider_id.strip()
        if not provider_id:
            return ""
        return self._provider_display_names.get(provider_id, provider_id)

    def _update_selection_status(self, selected_index: int) -> None:
        selection = self.query_one("#quick-nav-selection", Static)
        if not self._visible_articles:
            selection.update("Selected 0 of 0")
            return
        bounded_index = min(max(selected_index, 0), len(self._visible_articles) - 1)
        selection.update(f"Selected {bounded_index + 1} of {len(self._visible_articles)}")
