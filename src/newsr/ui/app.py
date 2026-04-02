from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.app import ScreenStackError
from textual.binding import Binding, BindingsMap
from textual.css.query import NoMatches
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Markdown, Static

from ..config.models import AppConfig
from ..domain import ArticleRecord
from ..domain.reader import ReaderState
from ..export import ExportAction, ExportService
from ..pipeline.refresh import NewsPipeline
from ..providers.llm.client import OpenAILLMClient
from ..providers.registry import build_provider_registry
from ..providers.search.duckduckgo import DuckDuckGoSearchClient
from ..providers.topic import TopicWatchProvider
from ..storage.facade import NewsStorage
from ..ui_text import UILocalizer
from .controllers.article_qa import ArticleQAController
from .controllers.article_categorization import ArticleCategorizationController
from .controllers.article_rendering import (
    article_frame_title,
    article_header,
    article_text,
    article_url_text,
    provider_display_names,
    visible_status_text,
)
from .controllers.export import ExportController
from .controllers.more_info import MoreInfoController
from .controllers.navigation import NavigationController
from .controllers.provider_home import ProviderHomeController
from .controllers.refresh import RefreshController
from .controllers.topic_watch import TopicWatchController
from .provider_home_table import ProviderHomeTable
from .screens import (
    HelpScreen,
    QuickNavScreen,
    SourceSelectionScreen,
)
from .themes import OLD_FIDO_THEME


class NewsReaderApp(App[None]):
    CSS = """
    Screen {
        background: $background;
        color: $foreground;
    }
    #chrome {
        height: 1fr;
    }
    #article-header {
        border: heavy $primary;
        background: $background;
        color: $primary;
        padding: 0 1;
        margin: 0;
        border-title-align: left;
    }
    #article-frame {
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
        background: $background;
    }
    #article-pane {
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
    #article-body {
        padding: 0 2 1 2;
        color: $foreground;
    }
    #article-url {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    #status {
        width: 1fr;
        color: $success;
        padding: 0;
    }
    #status-bar {
        height: 1;
        padding: 0 1;
    }
    #status-indicator {
        width: 3;
        margin-right: 1;
        color: $accent;
        display: none;
    }
    #help-text {
        background: $surface;
        color: $foreground;
        border: solid $secondary;
        padding: 1 2;
        width: 60;
        height: auto;
        margin: 4 8;
    }
    """

    BINDINGS = []

    def __init__(self, config: AppConfig, storage_path: Path, config_path: Path | None = None) -> None:
        super().__init__()
        self.ui = UILocalizer(config.ui.locale)
        palette_bindings = [
            binding
            for _key, binding in self._bindings
            if binding.system
        ]
        self._bindings = BindingsMap(self._build_bindings())
        for binding in palette_bindings:
            self._bindings._add_binding(binding)
        self.register_theme(OLD_FIDO_THEME)
        self.config = config
        self.config_path = config_path or Path("newsr.yml")
        self.storage = NewsStorage(storage_path)
        self.storage.initialize()
        self.builtin_providers = build_provider_registry()
        self.search_client = DuckDuckGoSearchClient()
        self.llm_client = OpenAILLMClient(config)
        self.providers = dict(self.builtin_providers)
        self.pipeline = NewsPipeline(config, self.storage, self.providers, self.llm_client)
        self.export_service = ExportService()

        # Controllers
        self._refresh = RefreshController(self)
        self._provider_home = ProviderHomeController(self)
        self._article_qa = ArticleQAController(self)
        self._article_categories = ArticleCategorizationController(self)
        self._more_info = MoreInfoController(self)
        self._navigation = NavigationController(self)
        self._export = ExportController(self)
        self._topic_watch = TopicWatchController(self)

        self._provider_home.bootstrap()
        self.rebuild_provider_registry()
        self.storage.prune_expired(config.articles.store)

        self._shutdown_requested = False
        self._exit_cleanup_done = False
        self._restoring_theme = False
        self.options = self.storage.load_options()
        self.reader_state = self.storage.load_reader_state(self._provider_home.active_scope_id)
        if self.options.theme_name and self.get_theme(self.options.theme_name) is not None:
            self._restoring_theme = True
            try:
                self.theme = self.options.theme_name
            finally:
                self._restoring_theme = False

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            Binding("left", "previous_article", self.ui.text("app.binding.previous"), show=False),
            Binding("right", "next_article", self.ui.text("app.binding.next"), show=False),
            Binding("up", "scroll_up", self.ui.text("app.binding.up"), show=False),
            Binding("down", "scroll_down", self.ui.text("app.binding.down"), show=False),
            Binding("pageup", "page_up", self.ui.text("app.binding.pgup"), show=False),
            Binding("pagedown", "page_down", self.ui.text("app.binding.pgdn"), show=False),
            Binding("b", "page_up", self.ui.text("app.binding.back"), show=False),
            ("k", "classify_article_categories", self.ui.text("app.binding.classify")),
            Binding("space", "space_down", self.ui.text("app.binding.space"), show=False),
            ("s", "toggle_summary", self.ui.text("app.binding.summary")),
            ("m", "show_or_refresh_more_info", self.ui.text("app.binding.more_info")),
            Binding("?", "show_article_qa", self.ui.text("app.binding.ask")),
            ("l", "show_quick_nav", self.ui.text("app.binding.list")),
            ("c", "show_source_manager", self.ui.text("app.binding.sources")),
            ("e", "export_current", self.ui.text("app.binding.export")),
            ("o", "open_article", self.ui.text("app.binding.open")),
            ("w", "watch_topic", self.ui.text("app.binding.watch_topic")),
            ("d", "download_articles", self.ui.text("app.binding.download")),
            ("h", "show_help", self.ui.text("app.binding.help")),
            Binding("ctrl+p", "command_palette", show=False),
            Binding("escape", "return_to_provider_home", self.ui.text("app.binding.providers"), show=False),
            ("q", "quit_reader", self.ui.text("app.binding.quit")),
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="chrome"):
            yield Static(id="article-header")
            with Vertical(id="article-frame"):
                yield ProviderHomeTable(id="provider-home-table", cursor_type="row")
                yield Static(id="provider-home-empty")
                with VerticalScroll(id="article-pane", can_focus=False):
                    yield Markdown(id="article-body")
                yield Static(id="article-url")
            with Horizontal(id="status-bar"):
                yield LoadingIndicator(id="status-indicator")
                yield Static(id="status")
        yield Footer()

    async def on_mount(self) -> None:
        self._sync_available = True
        provider_table = self.query_one("#provider-home-table", DataTable)
        provider_table.zebra_stripes = True
        provider_table.show_header = True
        provider_table.show_row_labels = False
        provider_table.show_cursor = True
        provider_table.display = False
        self.query_one("#provider-home-empty", Static).display = False
        self.load_articles()
        self.call_after_refresh(self.refresh_view)
        self.call_after_refresh(self.show_provider_home)
        self.call_after_refresh(self._refresh.run_due_refresh_if_idle)
        self.set_interval(60, self._refresh.run_due_refresh_if_idle, pause=False)

    def on_resize(self) -> None:
        self._invalidate_render_cache()

    # ------------------------------------------------------------------
    # Forwarding properties (article state on NavigationController)
    # ------------------------------------------------------------------

    @property
    def articles(self) -> list[ArticleRecord]:
        return self._navigation.articles

    @articles.setter
    def articles(self, value: list[ArticleRecord]) -> None:
        self._navigation.articles = value

    @property
    def current_index(self) -> int:
        return self._navigation.current_index

    @current_index.setter
    def current_index(self, value: int) -> None:
        self._navigation.current_index = value

    @property
    def current_article(self) -> ArticleRecord | None:
        return self._navigation.current_article

    @property
    def provider_home_open(self) -> bool:
        return self._provider_home.is_open

    @property
    def refresh_in_progress(self) -> bool:
        return self._refresh.in_progress

    @refresh_in_progress.setter
    def refresh_in_progress(self, value: bool) -> None:
        self._refresh.in_progress = value

    @property
    def status_text(self) -> str:
        return self._refresh.status_text

    @status_text.setter
    def status_text(self, value: str) -> None:
        self._refresh.status_text = value

    # ------------------------------------------------------------------
    # Forwarding methods (article loading, persistence, render cache)
    # ------------------------------------------------------------------

    def load_articles(
        self,
        *,
        preferred_article_id: str | None = None,
        auto_select_first: bool = False,
        fallback_to_current_article: bool = True,
    ) -> None:
        self._navigation.load_articles(
            preferred_article_id=preferred_article_id,
            auto_select_first=auto_select_first,
            fallback_to_current_article=fallback_to_current_article,
        )

    def _articles_for_scope(self, scope_id: str) -> list[ArticleRecord]:
        return self._navigation._articles_for_scope(scope_id)

    def _persist_reader_state(self) -> None:
        self._navigation.persist_reader_state()

    def _save_reader_state_now(self) -> None:
        self._navigation.save_reader_state_now()

    def _capture_reader_state(self) -> ReaderState:
        return self._navigation.capture_reader_state()

    def _invalidate_render_cache(self) -> None:
        self._navigation.invalidate_render_cache()

    @property
    def _auto_fetch_armed(self) -> bool:
        return self._navigation._auto_fetch_armed

    @_auto_fetch_armed.setter
    def _auto_fetch_armed(self, value: bool) -> None:
        self._navigation._auto_fetch_armed = value

    # ------------------------------------------------------------------
    # Action methods (thin forwarding to controllers)
    # ------------------------------------------------------------------

    def action_previous_article(self) -> None:
        self._navigation.previous()

    def action_next_article(self) -> None:
        self._navigation.next()

    def action_toggle_summary(self) -> None:
        self._navigation.toggle_summary()

    def action_classify_article_categories(self) -> None:
        self._article_categories.categorize_current()

    def action_scroll_up(self) -> None:
        self._navigation.scroll_up()

    def action_scroll_down(self) -> None:
        self._navigation.scroll_down()

    def action_page_up(self) -> None:
        self._navigation.page_up()

    def action_page_down(self) -> None:
        self._navigation.page_down()

    def action_space_down(self) -> None:
        if self.provider_home_open:
            self._provider_home.open_selected_scope()
            return
        self._navigation.space_down()

    def action_space_up(self) -> None:
        self._navigation.space_up()

    def action_open_article(self) -> None:
        self._navigation.open_article()

    def action_show_help(self) -> None:
        help_key = "help.body.provider_home" if self.provider_home_open else "help.body.reader"
        self.push_screen(HelpScreen(self.ui.text(help_key)))

    def action_show_or_refresh_more_info(self) -> None:
        if self.provider_home_open:
            return
        self.close_article_qa()
        self.refresh_more_info(force_refresh=self._more_info._screen is not None)

    def action_show_article_qa(self) -> None:
        if self.provider_home_open:
            return
        article = self.current_article
        if article is None:
            return
        self._article_qa.show(article)

    def action_show_quick_nav(self) -> None:
        if self.provider_home_open:
            return
        self.push_screen(
            QuickNavScreen(
                self.ui,
                self.articles,
                self.current_article.article_id if self.current_article else None,
                provider_display_names(self.storage),
            )
        )

    def action_show_source_manager(self) -> None:
        self.push_screen(
            SourceSelectionScreen(
                self.ui,
                default_schedule=self.config.articles.update_schedule,
            )
        )

    def action_show_category_picker(self) -> None:
        self.action_show_source_manager()

    def action_export_current(self) -> None:
        self._export.export_current()

    async def action_quit_reader(self) -> None:
        self._refresh.set_status_text(self.ui.text("app.status.exiting"), busy=False)
        self.refresh_view()
        self._refresh.shutdown()
        self._more_info.cancel()
        self._article_qa.cancel()
        self._article_categories.cancel()
        self._cleanup_before_exit()
        self._persist_reader_state()
        self.exit()

    def action_download_articles(self) -> None:
        provider_ids = self._manual_refresh_provider_ids()
        if provider_ids:
            self._refresh.start(provider_ids, force=True)

    def action_watch_topic(self) -> None:
        self._topic_watch.start()

    def action_return_to_provider_home(self) -> None:
        if self.provider_home_open:
            return
        if len(self.screen_stack) > 1:
            return
        self._save_reader_state_now()
        self.show_provider_home()

    # ------------------------------------------------------------------
    # Delegating methods (called by screens via self.app.*)
    # ------------------------------------------------------------------

    def submit_article_question(self, question: str) -> None:
        self._article_qa.submit(question)

    def close_article_qa(self) -> None:
        self._article_qa.close()

    def open_article_qa_source(self, index: int) -> None:
        self._article_qa.open_source(index)

    def refresh_more_info(self, *, force_refresh: bool) -> None:
        self._more_info.refresh(force_refresh=force_refresh)

    def close_more_info(self) -> None:
        self._more_info.close()

    def show_provider_home(self) -> None:
        self._provider_home.show()

    def close_provider_home(self) -> None:
        self._provider_home.close()

    def open_scope(self, scope_id: str) -> None:
        self._provider_home.open_scope(scope_id)

    def move_provider_home_cursor(self, delta: int) -> None:
        self._provider_home.move_cursor(delta)

    def page_provider_home(self, step: int) -> None:
        self._provider_home.page_cursor(step)

    def move_provider_home_to_boundary(self, *, first: bool) -> None:
        self._provider_home.move_to_boundary(first=first)

    def provider_home_rows(self) -> list:
        return self._provider_home.rows()

    def list_source_providers(self) -> list:
        return self._provider_home.list_providers()

    def list_source_targets(self, provider_id: str) -> list:
        return self._provider_home.list_targets(provider_id)

    def refresh_source_catalog(self, provider_id: str) -> list:
        return self._provider_home.refresh_catalog(provider_id)

    def apply_source_configuration(
        self,
        enabled_by_provider: dict[str, bool],
        selected_targets: dict[str, list[str]],
    ) -> bool:
        return self._provider_home.apply_configuration(enabled_by_provider, selected_targets)

    def update_provider_schedule(self, provider_id: str, update_schedule: str | None) -> None:
        self.storage.update_provider_schedule(provider_id, update_schedule)
        self._refresh.request_due_refresh_check()

    def create_topic_provider(
        self,
        *,
        display_name: str,
        topic_query: str,
        update_schedule: str | None,
        enabled: bool = True,
    ):
        provider = self.storage.create_topic_provider(
            display_name=display_name,
            topic_query=topic_query,
            update_schedule=update_schedule,
            enabled=enabled,
        )
        self.rebuild_provider_registry()
        return provider

    def delete_topic_provider(self, provider_id: str) -> None:
        self.storage.delete_provider(provider_id)
        self._provider_home.handle_deleted_provider(provider_id)
        self.rebuild_provider_registry()

    def open_article_by_id(self, article_id: str) -> None:
        self._navigation.open_by_id(article_id)

    def open_external_url(self, url: str) -> None:
        self._navigation.open_external_url(url)

    def set_status(self, value: str) -> None:
        self._refresh.set_status(value)

    def request_open_link(self, title: str, url: str) -> None:
        self._navigation.request_open_link(title, url)

    def confirm_open_link(self) -> None:
        self._navigation.confirm_open_link()

    def close_open_link_confirm(self) -> None:
        self._navigation.close_open_link_confirm()

    def run_export_action(self, action: ExportAction) -> None:
        self._export.run_export(action)

    def close_export_screen(self) -> None:
        self._export.close()

    # ------------------------------------------------------------------
    # Textual event handlers
    # ------------------------------------------------------------------

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        return self._provider_home.check_action(action)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._provider_home.handle_row_selected(event)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._provider_home.handle_row_highlighted(event)

    def _watch_theme(self, theme_name: str) -> None:
        super()._watch_theme(theme_name)
        self.options.theme_name = theme_name
        if self._restoring_theme:
            return
        self.storage.save_options(self.options)

    def on_unmount(self) -> None:
        self._cleanup_before_exit()
        self._persist_reader_state()
        if self._refresh._thread is None:
            self.storage.close()

    def rebuild_provider_registry(self) -> None:
        providers = dict(self.builtin_providers)
        for provider_record in self.storage.list_providers():
            if provider_record.provider_type != "topic":
                continue
            topic_query = provider_record.settings.get("topic_query", provider_record.display_name).strip()
            providers[provider_record.provider_id] = TopicWatchProvider(
                provider_id=provider_record.provider_id,
                display_name=provider_record.display_name,
                topic_query=topic_query,
                search_client=self.search_client,
            )
        self.providers = providers
        self.pipeline.providers = providers

    # ------------------------------------------------------------------
    # View rendering
    # ------------------------------------------------------------------

    def refresh_view(self) -> None:
        try:
            header = self.query_one("#article-header", Static)
            provider_table = self.query_one("#provider-home-table", DataTable)
            provider_empty = self.query_one("#provider-home-empty", Static)
            body = self.query_one("#article-body", Markdown)
            article_pane = self.query_one("#article-pane", VerticalScroll)
            article_url_widget = self.query_one("#article-url", Static)
            status = self.query_one("#status", Static)
            status_indicator = self.query_one("#status-indicator", LoadingIndicator)
            footer = self.query_one(Footer)
        except NoMatches:
            return
        nav = self._navigation
        footer.show_command_palette = not self.provider_home_open
        header.display = not self.provider_home_open
        if self.provider_home_open:
            provider_table.display = bool(provider_table.row_count)
            provider_empty.display = not provider_table.row_count
            article_pane.display = False
            article_url_widget.display = True
            border_title = None
            header_text = ""
            body_text = nav._rendered_body_text or ""
            url_text = ""
        else:
            provider_table.display = False
            provider_empty.display = False
            article_pane.display = True
            article_url_widget.display = True
            article = self.current_article
            if article is None:
                border_title = None
                header_text = self.ui.text("app.empty.header")
                body_text = self.ui.text("app.empty.body")
                url_text = ""
            else:
                border_title = article_frame_title(article, header.size.width, self.providers)
                active_theme = self.get_theme(self.theme)
                header_text = article_header(
                    self.ui,
                    self.current_index,
                    len(self.articles),
                    article,
                    self.reader_state,
                    active_theme.accent if active_theme is not None else "#ffffff",
                )
                body_text = article_text(self.reader_state, article)
                url_text = article_url_text(self.ui, article, article_url_widget.size.width)
        if header.display and header.size.width == 0:
            # Widget is visible but layout has not been computed yet.
            # Clear any stale border title and rerender after the next layout pass.
            header.border_title = None
            self.call_after_refresh(self.refresh_view)
        elif header.border_title != border_title:
            header.border_title = border_title
        if nav._rendered_header_text != header_text:
            header.update(header_text)
            nav._rendered_header_text = header_text
        if not self.provider_home_open and nav._rendered_body_text != body_text:
            body.update(body_text)
            nav._rendered_body_text = body_text
        if nav._rendered_article_url != url_text:
            article_url_widget.update(url_text)
            nav._rendered_article_url = url_text
        if not self.provider_home_open and nav._pending_scroll_restore:
            nav.schedule_scroll_restore()
        if status_indicator.display != self._refresh.status_busy:
            status_indicator.display = self._refresh.status_busy
        status_text_value = visible_status_text(self.status_text, self.size.width, self._refresh.status_busy)
        if nav._rendered_status_text != status_text_value:
            status.update(status_text_value)
            nav._rendered_status_text = status_text_value

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_before_exit(self) -> None:
        if self._exit_cleanup_done:
            return
        self.close_export_screen()
        self.close_open_link_confirm()
        self.close_article_qa()
        self._article_categories.cancel()
        self.close_more_info()
        self.close_provider_home()
        self.storage.delete_incomplete_articles()
        self.articles = self._articles_for_scope(self._provider_home.active_scope_id)
        if self.current_index >= len(self.articles):
            self.current_index = max(0, len(self.articles) - 1)
        self._navigation._state_persisted = False
        self._exit_cleanup_done = True

    def _manual_refresh_provider_ids(self) -> list[str]:
        if self.provider_home_open or self._provider_home.active_scope_id == "[ALL]":
            return [
                provider.provider_id
                for provider in self.storage.list_enabled_providers()
                if provider.provider_type != "all"
            ]
        provider_id = self._provider_home.active_scope_id
        provider = self.storage.get_provider(provider_id)
        if provider is None or provider.provider_type == "all":
            return []
        return [provider_id]
