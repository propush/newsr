from __future__ import annotations

import webbrowser
from dataclasses import dataclass, field, replace
from datetime import datetime
from itertools import count
from pathlib import Path
from threading import Thread
from time import monotonic

from rich.cells import cell_len
from textual.app import App, ComposeResult
from textual.app import ScreenStackError
from textual.binding import Binding, BindingsMap
from textual.css.query import NoMatches
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, LoadingIndicator, Markdown, Static

from ..cancellation import RefreshCancellation, RefreshCancelled
from ..config.models import AppConfig
from ..domain import ArticleRecord, ProviderRecord, ProviderTarget
from ..domain.reader import ReaderState, ViewMode
from ..export import ExportAction, ExportService
from ..pipeline.refresh import NewsPipeline
from ..providers.llm.client import OpenAILLMClient
from ..providers.registry import build_provider_registry
from ..providers.search.duckduckgo import DuckDuckGoSearchClient, SearchResult, normalize_result_url
from ..storage.facade import NewsStorage
from ..ui_text import UILocalizer
from .screens import (
    ArticleQuestionScreen,
    ExportScreen,
    HelpScreen,
    MoreInfoScreen,
    OpenLinkConfirmScreen,
    QuickNavScreen,
    SourceSelectionScreen,
)
from .themes import OLD_FIDO_THEME


@dataclass(slots=True)
class ArticleQuestionTurn:
    turn_id: int
    question: str
    answer: str | None = None
    error_text: str | None = None
    sources: list[SearchResult] = field(default_factory=list)
    pending: bool = False


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
        self.providers = build_provider_registry()
        self._bootstrap_provider_state()
        self.storage.prune_expired(config.articles.store)
        self.search_client = DuckDuckGoSearchClient()
        self.llm_client = OpenAILLMClient(config)
        self.pipeline = NewsPipeline(config, self.storage, self.providers, self.llm_client)
        self.export_service = ExportService()
        self.articles: list[ArticleRecord] = []
        self.current_index = 0
        self.status_text = self.ui.text("app.status.ready")
        self._status_busy = False
        self._status_override_until = 0.0
        self.refresh_in_progress = False
        self._auto_select_first_ready_article = False
        self._auto_fetch_armed = True
        self._refresh_thread: Thread | None = None
        self._refresh_cancellation: RefreshCancellation | None = None
        self._shutdown_requested = False
        self._state_persisted = False
        self._exit_cleanup_done = False
        self._restoring_theme = False
        self._more_info_cache: dict[str, str] = {}
        self._more_info_screen: MoreInfoScreen | None = None
        self._more_info_thread: Thread | None = None
        self._more_info_cancellation: RefreshCancellation | None = None
        self._more_info_article_id: str | None = None
        self._article_qa_screen: ArticleQuestionScreen | None = None
        self._article_qa_thread: Thread | None = None
        self._article_qa_cancellation: RefreshCancellation | None = None
        self._article_qa_article_id: str | None = None
        self._article_qa_turns: list[ArticleQuestionTurn] = []
        self._article_qa_turn_ids = count(1)
        self._export_screen: ExportScreen | None = None
        self._open_link_confirm_screen: OpenLinkConfirmScreen | None = None
        self._pending_open_link: tuple[str, str] | None = None
        self.reader_state = self.storage.load_reader_state()
        self._rendered_header_text: str | None = None
        self._rendered_body_text: str | None = None
        self._rendered_article_url: str | None = None
        self._rendered_status_text: str | None = None
        if self.reader_state.theme_name and self.get_theme(self.reader_state.theme_name) is not None:
            self._restoring_theme = True
            try:
                self.theme = self.reader_state.theme_name
            finally:
                self._restoring_theme = False

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            ("left", "previous_article", self.ui.text("app.binding.previous")),
            ("right", "next_article", self.ui.text("app.binding.next")),
            ("up", "scroll_up", self.ui.text("app.binding.up")),
            ("down", "scroll_down", self.ui.text("app.binding.down")),
            ("pageup", "page_up", self.ui.text("app.binding.pgup")),
            ("pagedown", "page_down", self.ui.text("app.binding.pgdn")),
            Binding("b", "page_up", self.ui.text("app.binding.back"), show=False),
            Binding("space", "space_down", self.ui.text("app.binding.space"), show=False),
            ("s", "toggle_summary", self.ui.text("app.binding.summary")),
            ("m", "show_or_refresh_more_info", self.ui.text("app.binding.more_info")),
            Binding("?", "show_article_qa", self.ui.text("app.binding.ask")),
            ("l", "show_quick_nav", self.ui.text("app.binding.list")),
            ("c", "show_source_manager", self.ui.text("app.binding.sources")),
            ("e", "export_current", self.ui.text("app.binding.export")),
            ("o", "open_article", self.ui.text("app.binding.open")),
            ("d", "download_articles", self.ui.text("app.binding.download")),
            ("h", "show_help", self.ui.text("app.binding.help")),
            ("q", "quit_reader", self.ui.text("app.binding.quit")),
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="chrome"):
            yield Static(id="article-header")
            with Vertical(id="article-frame"):
                with VerticalScroll(id="article-pane"):
                    yield Markdown(id="article-body")
                yield Static(id="article-url")
            with Horizontal(id="status-bar"):
                yield LoadingIndicator(id="status-indicator")
                yield Static(id="status")
        yield Footer()

    async def on_mount(self) -> None:
        # Force synchronized output so frame updates are atomic on the terminal
        # side.  Without this, terminals that fail DEC-2026 detection (common
        # over SSH) display partial frames, causing border artifacts.
        self._sync_available = True
        self.load_articles()
        self.call_after_refresh(self.refresh_view)
        self._start_refresh()

    def on_resize(self) -> None:
        self._invalidate_render_cache()

    def _invalidate_render_cache(self) -> None:
        """Clear width-dependent cached text so the next refresh_view picks up new sizes."""
        self._rendered_article_url = None
        self._rendered_status_text = None

    def _bootstrap_provider_state(self) -> None:
        provider_records = [
            ProviderRecord(
                provider_id=provider.provider_id,
                display_name=provider.display_name,
                enabled=(provider.provider_id == "bbc"),
            )
            for provider in self.providers.values()
        ]
        self.storage.sync_providers(provider_records)
        for provider in self.providers.values():
            if self.storage.list_provider_targets(provider.provider_id):
                continue
            default_targets = provider.default_targets()
            self.storage.replace_provider_targets(provider.provider_id, default_targets)
            self.storage.set_selected_targets(
                provider.provider_id,
                [target.target_key for target in default_targets if target.selected],
            )

    def load_articles(
        self,
        *,
        preferred_article_id: str | None = None,
        auto_select_first: bool = False,
    ) -> None:
        current_article = self.current_article
        previous_count = len(self.articles)
        self.articles = self.storage.list_articles()
        if len(self.articles) > previous_count:
            self._auto_fetch_armed = True
        self.current_index = self._resolve_current_index(
            preferred_article_id=preferred_article_id or (current_article.article_id if current_article else None),
            auto_select_first=auto_select_first,
        )
        self._sync_reader_state_after_article_load()
        try:
            self.refresh_view()
        except (NoMatches, ScreenStackError):
            pass

    def refresh_view(self) -> None:
        try:
            header = self.query_one("#article-header", Static)
            body = self.query_one("#article-body", Markdown)
            article_url = self.query_one("#article-url", Static)
            status = self.query_one("#status", Static)
            status_indicator = self.query_one("#status-indicator", LoadingIndicator)
        except NoMatches:
            return
        article = self.current_article
        if article is None:
            border_title = None
            header_text = self.ui.text("app.empty.header")
            body_text = self.ui.text("app.empty.body")
            article_url_text = ""
        else:
            border_title = self._article_frame_title(article, header.size.width)
            header_text = self._article_header(article)
            body_text = self._article_text(article)
            article_url_text = self._article_url_text(article, article_url.size.width)
        if header.border_title != border_title:
            header.border_title = border_title
        if self._rendered_header_text != header_text:
            header.update(header_text)
            self._rendered_header_text = header_text
        if self._rendered_body_text != body_text:
            body.update(body_text)
            self._rendered_body_text = body_text
        if self._rendered_article_url != article_url_text:
            article_url.update(article_url_text)
            self._rendered_article_url = article_url_text
        if status_indicator.display != self._status_busy:
            status_indicator.display = self._status_busy
        status_text = self._visible_status_text(self.size.width)
        if self._rendered_status_text != status_text:
            status.update(status_text)
            self._rendered_status_text = status_text

    @property
    def current_article(self) -> ArticleRecord | None:
        if not self.articles:
            return None
        return self.articles[self.current_index]

    def action_previous_article(self) -> None:
        if self._article_qa_screen is not None:
            return
        if self.current_index == 0:
            return
        self.close_more_info()
        self.current_index -= 1
        self._reset_scroll()
        self.refresh_view()
        self._save_reader_state_now()
        self._maybe_auto_fetch()

    def action_next_article(self) -> None:
        if self._article_qa_screen is not None:
            return
        if self.current_index >= len(self.articles) - 1:
            return
        self.close_more_info()
        self.current_index += 1
        self._reset_scroll()
        self.refresh_view()
        self._save_reader_state_now()
        self._maybe_auto_fetch()

    def action_toggle_summary(self) -> None:
        article = self.current_article
        if article is None or not article.summary:
            return
        self.reader_state.view_mode = (
            ViewMode.SUMMARY if self.reader_state.view_mode == ViewMode.FULL else ViewMode.FULL
        )
        self.refresh_view()
        self._save_reader_state_now()

    def action_scroll_up(self) -> None:
        self.query_one("#article-pane", VerticalScroll).scroll_relative(y=-3, animate=False)

    def action_scroll_down(self) -> None:
        self.query_one("#article-pane", VerticalScroll).scroll_relative(y=3, animate=False)

    def action_page_up(self) -> None:
        self.query_one("#article-pane", VerticalScroll).scroll_page_up()

    def action_page_down(self) -> None:
        self.query_one("#article-pane", VerticalScroll).scroll_page_down()

    def action_space_down(self) -> None:
        pane = self.query_one("#article-pane", VerticalScroll)
        if pane.scroll_target_y >= max(0, pane.max_scroll_y - 1):
            self.action_next_article()
            return
        self.action_page_down()

    def action_space_up(self) -> None:
        self.action_page_up()

    def action_open_article(self) -> None:
        article = self.current_article
        if article is None:
            return
        self.open_external_url(article.url)

    def open_external_url(self, url: str) -> None:
        normalized_url = normalize_result_url(url)
        try:
            opened = webbrowser.open(normalized_url, new=2)
        except Exception as exc:
            self._set_status_text(self.ui.text("app.status.browser_open_failed", error=exc), busy=False, hold_seconds=1.0)
        else:
            self._set_status_text(
                self.ui.text("app.status.browser_opened")
                if opened
                else self.ui.text("app.status.browser_not_confirmed"),
                busy=False,
                hold_seconds=1.0,
            )
        self.refresh_view()

    def run_export_action(self, action: ExportAction) -> None:
        article = self.current_article
        if article is None:
            self.close_export_screen()
            self._set_status_text(self.ui.text("app.status.no_article_to_export"), busy=False, hold_seconds=1.0)
            self.refresh_view()
            return
        result = self.export_service.export(
            action,
            article=article,
            view_mode=self.reader_state.view_mode,
            theme=self.get_theme(self.theme),
            config=self.config,
        )
        self._set_status_text(result.message, busy=False, hold_seconds=1.2)
        if result.success:
            self.close_export_screen()
        self.refresh_view()

    def close_export_screen(self) -> None:
        screen = self._export_screen
        self._export_screen = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen(self.ui))

    def action_show_or_refresh_more_info(self) -> None:
        self.close_article_qa()
        self.refresh_more_info(force_refresh=self._more_info_screen is not None)

    def action_show_article_qa(self) -> None:
        article = self.current_article
        if article is None:
            return
        self.close_more_info()
        screen = self._ensure_article_qa_screen(article)
        screen.focus_input()

    def action_show_quick_nav(self) -> None:
        self.push_screen(
            QuickNavScreen(
                self.ui,
                self.articles,
                self.current_article.article_id if self.current_article else None,
                self._provider_display_names(),
            )
        )

    def action_show_source_manager(self) -> None:
        self.push_screen(SourceSelectionScreen(self.ui))

    def action_show_category_picker(self) -> None:
        self.action_show_source_manager()

    def action_export_current(self) -> None:
        if len(self.screen_stack) > 1:
            return
        article = self.current_article
        if article is None:
            self._set_status_text(self.ui.text("app.status.no_article_to_export"), busy=False, hold_seconds=1.0)
            self.refresh_view()
            return
        if self._export_screen is not None:
            return
        self._export_screen = ExportScreen(
            self.ui,
            article.translated_title or article.title,
            self._view_mode_label(article),
        )
        self.push_screen(self._export_screen)

    async def action_quit_reader(self) -> None:
        self._set_status_text(self.ui.text("app.status.exiting"), busy=False)
        self.refresh_view()
        self._shutdown_refresh()
        self._cancel_more_info_lookup()
        self._cleanup_before_exit()
        self._persist_reader_state()
        self.exit()

    def action_download_articles(self) -> None:
        self._start_refresh()

    def list_source_providers(self) -> list[ProviderRecord]:
        return self.storage.list_providers()

    def list_source_targets(self, provider_id: str) -> list[ProviderTarget]:
        return self.storage.list_provider_targets(provider_id)

    def refresh_source_catalog(self, provider_id: str) -> list[ProviderTarget]:
        provider = self.providers[provider_id]
        current_selected = {
            target.target_key for target in self.storage.list_selected_targets(provider_id)
        }
        targets = provider.discover_targets()
        self.storage.replace_provider_targets(provider_id, targets)
        selected_keys = [target.target_key for target in targets if target.target_key in current_selected]
        if not selected_keys:
            selected_keys = [target.target_key for target in targets if target.selected]
        self.storage.set_selected_targets(provider_id, selected_keys)
        return self.storage.list_provider_targets(provider_id)

    def apply_source_configuration(
        self,
        enabled_by_provider: dict[str, bool],
        selected_targets: dict[str, list[str]],
    ) -> bool:
        current_enabled = {
            provider.provider_id: provider.enabled for provider in self.storage.list_providers()
        }
        current_selected = {
            provider.provider_id: sorted(
                target.target_key for target in self.storage.list_selected_targets(provider.provider_id)
            )
            for provider in self.storage.list_providers()
        }
        if enabled_by_provider == current_enabled and selected_targets == current_selected:
            self._set_status_text(self.ui.text("app.status.sources_unchanged"), busy=False)
            self.refresh_view()
            return True
        for provider_id, enabled in enabled_by_provider.items():
            self.storage.set_provider_enabled(provider_id, enabled)
        for provider_id, target_keys in selected_targets.items():
            self.storage.set_selected_targets(provider_id, target_keys)
        if self.refresh_in_progress:
            self._set_status_text(
                self.ui.text("app.status.sources_saved_next_refresh"),
                busy=False,
            )
            self.refresh_view()
            return True
        self._set_status_text(self.ui.text("app.status.sources_saved_refreshing"), busy=False)
        self.refresh_view()
        self._start_refresh()
        return True

    def open_article_by_id(self, article_id: str) -> None:
        if self._article_qa_screen is not None:
            return
        for index, article in enumerate(self.articles):
            if article.article_id != article_id:
                continue
            self.close_more_info()
            self.current_index = index
            self._reset_scroll()
            self.refresh_view()
            self._save_reader_state_now()
            self._maybe_auto_fetch()
            return

    def _start_refresh(self) -> None:
        if self.refresh_in_progress or self._shutdown_requested:
            return
        self.refresh_in_progress = True
        self._auto_fetch_armed = False
        self._auto_select_first_ready_article = not self.articles
        self._refresh_cancellation = RefreshCancellation()
        self._refresh_thread = self._launch_refresh_thread()

    def _launch_refresh_thread(self) -> Thread:
        thread = Thread(target=self._run_refresh, name="newsr-refresh", daemon=True)
        thread.start()
        return thread

    def _run_refresh(self) -> None:
        try:
            self.pipeline.refresh(
                self.set_status,
                self._handle_article_ready,
                self._refresh_cancellation,
            )
        finally:
            self._call_from_thread_if_ready(self._finish_refresh)

    def _finish_refresh(self) -> None:
        self.refresh_in_progress = False
        self._status_busy = False
        if not self._shutdown_requested:
            self.load_articles()
        self._refresh_thread = None
        self._refresh_cancellation = None

    def _watch_theme(self, theme_name: str) -> None:
        super()._watch_theme(theme_name)
        self.reader_state.theme_name = theme_name
        if self._restoring_theme:
            return
        self.storage.save_reader_state(self._capture_reader_state())
        self._state_persisted = False

    def on_unmount(self) -> None:
        self._cleanup_before_exit()
        self._persist_reader_state()
        if self._refresh_thread is None:
            self.storage.close()

    def set_status(self, value: str) -> None:
        localized_value = self.ui.status(value)
        if localized_value != self.ui.text("app.status.ready") and monotonic() < self._status_override_until:
            return
        self._set_status_text(
            localized_value,
            busy=value.startswith(("fetching ", "extracting ", "translating ", "summarizing ")),
        )
        self._call_from_thread_if_ready(self.refresh_view)

    def _set_status_text(
        self,
        value: str,
        *,
        busy: bool | None = None,
        hold_seconds: float = 0.0,
    ) -> None:
        self.status_text = value
        self._status_busy = self._status_busy_for(value) if busy is None else busy
        self._status_override_until = monotonic() + hold_seconds if hold_seconds > 0 else 0.0

    @staticmethod
    def _status_busy_for(value: str) -> bool:
        return value.startswith(("fetching ", "extracting ", "translating ", "summarizing "))

    def _handle_article_ready(self, article_id: str) -> None:
        self._call_from_thread_if_ready(self._load_ready_article, article_id)

    def _call_from_thread_if_ready(self, callback, *args) -> bool:  # type: ignore[no-untyped-def]
        if not self.is_mounted:
            return False
        loop = getattr(self, "_loop", None)
        if loop is None or loop.is_closed():
            return False
        try:
            self.call_from_thread(callback, *args)
        except RuntimeError:
            return False
        return True

    def _load_ready_article(self, article_id: str) -> None:
        auto_select_first = self._auto_select_first_ready_article and not self.articles
        self.load_articles(auto_select_first=auto_select_first)
        if auto_select_first and self.articles:
            self._auto_select_first_ready_article = False

    def _resolve_current_index(
        self,
        *,
        preferred_article_id: str | None = None,
        auto_select_first: bool = False,
    ) -> int:
        if not self.articles:
            return 0
        if auto_select_first:
            return 0
        article_id = preferred_article_id or self.reader_state.article_id
        if article_id is None:
            return 0
        for index, article in enumerate(self.articles):
            if article.article_id == article_id:
                return index
        return 0

    def _sync_reader_state_after_article_load(self) -> None:
        article = self.current_article
        self.reader_state.article_id = article.article_id if article else None
        if article is None:
            self.reader_state.scroll_offset = 0

    def _article_text(self, article: ArticleRecord) -> str:
        if self.reader_state.view_mode == ViewMode.SUMMARY and article.summary:
            return article.summary
        return article.translated_body or article.source_body

    def _view_mode_label(self, article: ArticleRecord) -> str:
        if self.reader_state.view_mode == ViewMode.SUMMARY and article.summary:
            return self.ui.text("app.article.mode.summary")
        return self.ui.text("app.article.mode.full")

    def _article_header(self, article: ArticleRecord) -> str:
        date_text = self._format_article_date(article)
        title = article.translated_title or article.title
        mode = self._view_mode_label(article)
        article_position = self.current_index + 1
        lines = [
            self.ui.text("app.article.position", current=article_position, total=len(self.articles)),
            self.ui.text("app.article.date", date=date_text),
        ]
        lines.extend(
            [
                self.ui.text("app.article.title", title=title),
                self.ui.text("app.article.mode", mode=mode),
            ]
        )
        return "\n".join(lines)

    def _article_frame_title(self, article: ArticleRecord, width: int) -> str | None:
        category = article.category.strip()
        source_label = self._article_source_label(article)
        if not category and source_label is None:
            return None
        if source_label is None:
            return category if category else None
        left = f"{source_label} "
        if not category:
            return source_label
        right = f" {category}"
        available = max(1, width - 4)
        minimum_gap = 1
        max_left = max(1, available - cell_len(right) - minimum_gap)
        if cell_len(left) > max_left:
            left = self._truncate_cells(left, max_left)
        gap = max(minimum_gap, available - cell_len(left) - cell_len(right))
        return f"{left}{'━' * gap}{right}"

    def _visible_status_text(self, viewport_width: int) -> str:
        if viewport_width <= 0:
            return self.status_text
        status_bar_padding = 2
        busy_indicator_width = 4 if self._status_busy else 0
        available = max(1, viewport_width - status_bar_padding - busy_indicator_width)
        return self._format_status_text(self.status_text, available)

    @classmethod
    def _format_status_text(cls, value: str, max_cells: int) -> str:
        if max_cells <= 0 or cell_len(value) <= max_cells:
            return value
        progress_marker = ", done "
        progress_index = value.rfind(progress_marker)
        if progress_index == -1:
            return cls._truncate_middle_cells(value, max_cells)

        progress = value[progress_index + 2 :]
        separator = "… "
        if cell_len(progress) + cell_len(separator) >= max_cells:
            return cls._truncate_cells(progress, max_cells)

        prefix_width = max_cells - cell_len(progress) - cell_len(separator)
        prefix = cls._fit_cells(value[:progress_index], prefix_width)
        return f"{prefix}{separator}{progress}"

    @staticmethod
    def _truncate_cells(text: str, max_cells: int) -> str:
        if max_cells <= 0:
            return ""
        if cell_len(text) <= max_cells:
            return text
        if max_cells == 1:
            return "…"
        return f"{NewsReaderApp._fit_cells(text, max_cells - 1)}…"

    @classmethod
    def _truncate_middle_cells(cls, text: str, max_cells: int) -> str:
        if max_cells <= 0:
            return ""
        if cell_len(text) <= max_cells:
            return text
        if max_cells == 1:
            return "…"
        prefix_width = max(1, (max_cells - 1) // 2)
        suffix_width = max(1, max_cells - prefix_width - 1)
        prefix = cls._fit_cells(text, prefix_width)
        suffix = cls._fit_cells(text, suffix_width, from_end=True)
        return f"{prefix}…{suffix}"

    @staticmethod
    def _fit_cells(text: str, max_cells: int, *, from_end: bool = False) -> str:
        if max_cells <= 0:
            return ""
        if cell_len(text) <= max_cells:
            return text
        fitted = ""
        characters = reversed(text) if from_end else text
        for character in characters:
            if cell_len(character + fitted if from_end else fitted + character) > max_cells:
                break
            fitted = character + fitted if from_end else fitted + character
        return fitted

    def _article_source_label(self, article: ArticleRecord) -> str | None:
        author = article.author.strip() if article.author and article.author.strip() else None
        provider_label = None
        if article.provider_id and article.provider_id.strip():
            provider_id = article.provider_id.strip()
            provider = self.providers.get(provider_id)
            provider_label = provider.display_name if provider is not None else provider_id
        if author and provider_label:
            return f"{author} @ {provider_label}"
        if provider_label:
            return provider_label
        return author

    def _provider_display_names(self) -> dict[str, str]:
        return {
            provider.provider_id: provider.display_name
            for provider in self.storage.list_providers()
        }

    def _article_url_text(self, article: ArticleRecord, width: int | None = None) -> str:
        value = self.ui.text("app.article.url", url=article.url)
        if width is None or width <= 0:
            return value
        return self._truncate_middle_cells(value, width)

    @staticmethod
    def _format_article_date(article: ArticleRecord) -> str:
        date = article.published_at or article.created_at
        return date.astimezone().strftime("%Y-%m-%d %H:%M %Z")

    def _reset_scroll(self) -> None:
        self.reader_state.scroll_offset = 0
        self.query_one("#article-pane", VerticalScroll).scroll_to(y=0, animate=False)

    def _maybe_auto_fetch(self) -> None:
        if not self.articles or not self._auto_fetch_armed:
            return
        trigger_index = max(0, len(self.articles) - 5)
        if self.current_index < trigger_index:
            return
        self._auto_fetch_armed = False
        self._start_refresh()

    def _persist_reader_state(self) -> None:
        if self._state_persisted:
            return
        self.storage.save_reader_state(self._capture_reader_state())
        self._state_persisted = True

    def _save_reader_state_now(self) -> None:
        self._state_persisted = False
        self._persist_reader_state()

    def _capture_reader_state(self) -> ReaderState:
        article = self.current_article
        self.reader_state.article_id = article.article_id if article else None
        try:
            pane = self.query_one("#article-pane", VerticalScroll)
            self.reader_state.scroll_offset = int(pane.scroll_y)
        except (NoMatches, ScreenStackError):
            pass
        self.reader_state.theme_name = self.theme
        return self.reader_state

    def _shutdown_refresh(self) -> None:
        self._shutdown_requested = True
        cancellation = self._refresh_cancellation
        if cancellation is not None:
            cancellation.cancel()

    def _cleanup_before_exit(self) -> None:
        if self._exit_cleanup_done:
            return
        self.close_export_screen()
        self.close_open_link_confirm()
        self.close_article_qa()
        self.close_more_info()
        self.storage.delete_incomplete_articles()
        self.articles = self.storage.list_articles()
        if self.current_index >= len(self.articles):
            self.current_index = max(0, len(self.articles) - 1)
        self._state_persisted = False
        self._exit_cleanup_done = True

    def submit_article_question(self, question: str) -> None:
        article = self.current_article
        if article is None:
            return
        cleaned_question = question.strip()
        if not cleaned_question or self._article_qa_cancellation is not None:
            return
        chat_history = self._article_qa_history()
        turn = ArticleQuestionTurn(
            turn_id=next(self._article_qa_turn_ids),
            question=cleaned_question,
            pending=True,
        )
        self._article_qa_turns.append(turn)
        screen = self._ensure_article_qa_screen(article)
        screen.set_question("")
        self._update_article_qa_loading_state(article, "asking configured llm for web search query...")
        self._start_article_qa_request(article, turn.turn_id, cleaned_question, chat_history)

    def close_article_qa(self) -> None:
        self._cancel_article_qa_request(clear_turns=True)
        self._dismiss_article_qa_screen()

    def open_article_qa_source(self, index: int) -> None:
        sources = self._article_qa_visible_sources()
        if index < 0 or index >= len(sources):
            return
        source = sources[index]
        self.request_open_link(source.title, source.url)

    def request_open_link(self, title: str, url: str) -> None:
        normalized_url = normalize_result_url(url)
        self.close_open_link_confirm()
        self._pending_open_link = (title, normalized_url)
        screen = OpenLinkConfirmScreen(self.ui, title, normalized_url)
        self._open_link_confirm_screen = screen
        self.push_screen(screen)

    def confirm_open_link(self) -> None:
        pending = self._pending_open_link
        self.close_open_link_confirm()
        if pending is None:
            return
        _, url = pending
        self.open_external_url(url)

    def close_open_link_confirm(self) -> None:
        screen = self._open_link_confirm_screen
        self._open_link_confirm_screen = None
        self._pending_open_link = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass

    def _ensure_article_qa_screen(self, article: ArticleRecord) -> ArticleQuestionScreen:
        existing = self._article_qa_screen
        if existing is not None:
            if self._article_qa_article_id != article.article_id:
                self.close_article_qa()
            else:
                existing.article_title = article.translated_title or article.title
                existing.update_header()
                existing.set_content(self._article_qa_transcript())
                existing.set_sources(self._article_qa_source_links())
                return existing
        screen = ArticleQuestionScreen(self.ui, article.translated_title or article.title)
        self._article_qa_screen = screen
        self._article_qa_article_id = article.article_id
        self.push_screen(screen)
        screen.set_content(self._article_qa_transcript())
        screen.set_sources(self._article_qa_source_links())
        return screen

    def _start_article_qa_request(
        self,
        article: ArticleRecord,
        turn_id: int,
        question: str,
        chat_history: list[tuple[str, str]],
    ) -> None:
        self._cancel_article_qa_request(clear_turns=False)
        cancellation = RefreshCancellation()
        self._article_qa_cancellation = cancellation
        self._article_qa_article_id = article.article_id
        self._article_qa_thread = Thread(
            target=self._run_article_qa_request,
            args=(article, turn_id, question, chat_history, cancellation),
            name="newsr-article-qa",
            daemon=True,
        )
        self._article_qa_thread.start()

    def _run_article_qa_request(
        self,
        article: ArticleRecord,
        turn_id: int,
        question: str,
        chat_history: list[tuple[str, str]],
        cancellation: RefreshCancellation,
    ) -> None:
        current_datetime = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        try:
            original_article_title = article.title
            original_article_text = self._article_context_source_text(article)
            self._schedule_article_qa_progress(article, cancellation, "asking configured llm for web search query...")
            query = self.llm_client.build_article_question_query(
                original_article_title,
                original_article_text,
                question,
                current_datetime,
                chat_history,
                cancellation,
            ).strip()
            if not query:
                query = original_article_title
            self._schedule_article_qa_progress(article, cancellation, "searching DuckDuckGo...")
            results = self.search_client.search(query, cancellation=cancellation)
            self._schedule_article_qa_progress(article, cancellation, "asking configured llm to answer...")
            answer = self.llm_client.answer_article_question(
                original_article_title,
                original_article_text,
                question,
                current_datetime,
                chat_history,
                results,
                cancellation,
            )
        except RefreshCancelled:
            return
        except Exception as exc:
            if self.is_mounted:
                self.call_from_thread(
                    self._finish_article_qa_error,
                    article.article_id,
                    turn_id,
                    cancellation,
                    str(exc),
                )
            return
        if self.is_mounted:
            self.call_from_thread(
                self._finish_article_qa_success,
                article.article_id,
                turn_id,
                cancellation,
                answer,
                results,
            )

    def _finish_article_qa_success(
        self,
        article_id: str,
        turn_id: int,
        cancellation: RefreshCancellation,
        answer: str,
        sources: list[SearchResult],
    ) -> None:
        if cancellation is not self._article_qa_cancellation or article_id != self._article_qa_article_id:
            return
        self._article_qa_thread = None
        self._article_qa_cancellation = None
        turn = self._find_article_qa_turn(turn_id)
        if turn is None:
            return
        turn.pending = False
        turn.answer = answer
        turn.sources = list(sources)
        if self._article_qa_screen is not None:
            self._article_qa_screen.set_loading(False)
            self._article_qa_screen.set_status("ready")
            self._article_qa_screen.set_content(self._article_qa_transcript())
            self._article_qa_screen.set_sources(self._article_qa_source_links())
            self._article_qa_screen.focus_input()

    def _finish_article_qa_error(
        self,
        article_id: str,
        turn_id: int,
        cancellation: RefreshCancellation,
        error_text: str,
    ) -> None:
        if cancellation is not self._article_qa_cancellation or article_id != self._article_qa_article_id:
            return
        self._article_qa_thread = None
        self._article_qa_cancellation = None
        turn = self._find_article_qa_turn(turn_id)
        if turn is None:
            return
        turn.pending = False
        turn.error_text = error_text
        if self._article_qa_screen is not None:
            self._article_qa_screen.set_loading(False)
            self._article_qa_screen.set_status("failed")
            self._article_qa_screen.set_content(self._article_qa_transcript())
            self._article_qa_screen.set_sources(self._article_qa_source_links())
            self._article_qa_screen.focus_input()

    def _cancel_article_qa_request(self, *, clear_turns: bool) -> None:
        cancellation = self._article_qa_cancellation
        self._article_qa_cancellation = None
        self._article_qa_thread = None
        if cancellation is not None:
            cancellation.cancel()
        if clear_turns:
            self._article_qa_turns = []

    def _dismiss_article_qa_screen(self) -> None:
        screen = self._article_qa_screen
        self._article_qa_screen = None
        self._article_qa_article_id = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass

    def _schedule_article_qa_progress(
        self,
        article: ArticleRecord,
        cancellation: RefreshCancellation,
        stage: str,
    ) -> None:
        if self.is_mounted:
            self.call_from_thread(self._handle_article_qa_progress, article, cancellation, stage)

    def _handle_article_qa_progress(
        self,
        article: ArticleRecord,
        cancellation: RefreshCancellation,
        stage: str,
    ) -> None:
        if cancellation is not self._article_qa_cancellation or article.article_id != self._article_qa_article_id:
            return
        self._update_article_qa_loading_state(article, stage)

    def _update_article_qa_loading_state(self, article: ArticleRecord, stage: str) -> None:
        screen = self._ensure_article_qa_screen(article)
        screen.set_loading(True)
        screen.set_status(stage)
        screen.set_content(self._article_qa_transcript())
        screen.set_sources(self._article_qa_source_links())

    def _article_qa_transcript(self) -> str:
        if not self._article_qa_turns:
            return self.ui.text("article_qa.transcript.empty")
        sections = [self.ui.text("article_qa.transcript.title")]
        for index, turn in enumerate(self._article_qa_turns, start=1):
            sections.append(self.ui.text("article_qa.transcript.question", index=index, question=turn.question))
            if turn.pending:
                sections.append(self.ui.text("article_qa.transcript.pending"))
                continue
            if turn.error_text is not None:
                sections.append(self.ui.text("article_qa.transcript.answer_unavailable", error=turn.error_text))
                continue
            sections.append(
                self.ui.text(
                    "article_qa.transcript.answer",
                    answer=turn.answer or self.ui.text("article_qa.transcript.no_answer"),
                )
            )
            sections.append(self._article_qa_sources_markdown(turn.sources))
        return "\n\n".join(sections)

    def _article_qa_sources_markdown(self, sources: list[SearchResult]) -> str:
        if not sources:
            return self.ui.text("article_qa.transcript.sources_empty")
        lines = [self.ui.text("article_qa.transcript.sources_title")]
        for index, source in enumerate(sources, start=1):
            lines.append(f"{index}. [{source.title}]({source.url})")
        return "\n".join(lines)

    def _article_qa_history(self) -> list[tuple[str, str]]:
        return [
            (turn.question, turn.answer or "")
            for turn in self._article_qa_answered_turns()
        ]

    def _article_qa_answered_turns(self) -> list[ArticleQuestionTurn]:
        return [
            turn
            for turn in self._article_qa_turns
            if not turn.pending and turn.answer is not None and turn.error_text is None
        ]

    def _find_article_qa_turn(self, turn_id: int) -> ArticleQuestionTurn | None:
        for turn in self._article_qa_turns:
            if turn.turn_id == turn_id:
                return turn
        return None

    def _article_qa_visible_sources(self) -> list[SearchResult]:
        for turn in reversed(self._article_qa_turns):
            if turn.pending or turn.error_text is not None:
                continue
            return turn.sources
        return []

    def _article_qa_source_links(self) -> list[tuple[str, str]]:
        return [(source.title, source.url) for source in self._article_qa_visible_sources()]

    def refresh_more_info(self, *, force_refresh: bool) -> None:
        article = self.current_article
        if article is None:
            return
        screen = self._ensure_more_info_screen(article)
        cached = self._persisted_or_cached_more_info(article)
        if cached is not None and not force_refresh:
            screen.set_loading(False)
            screen.set_status("cached")
            screen.set_content(cached)
            self._more_info_cache[article.article_id] = cached
            return
        self._update_more_info_loading_state(article, "asking configured llm for search query...")
        self._start_more_info_lookup(article)

    def close_more_info(self) -> None:
        self._cancel_more_info_lookup()
        self._dismiss_more_info_screen()

    def _ensure_more_info_screen(self, article: ArticleRecord) -> MoreInfoScreen:
        existing = self._more_info_screen
        if existing is not None:
            if self._more_info_article_id != article.article_id:
                self.close_more_info()
            else:
                existing.article_title = article.translated_title or article.title
                existing.update_header()
                return existing
        screen = MoreInfoScreen(self.ui, article.translated_title or article.title)
        self._more_info_screen = screen
        self._more_info_article_id = article.article_id
        self.push_screen(screen)
        return screen

    def _start_more_info_lookup(self, article: ArticleRecord) -> None:
        self._cancel_more_info_lookup()
        cancellation = RefreshCancellation()
        self._more_info_cancellation = cancellation
        self._more_info_article_id = article.article_id
        self._more_info_thread = Thread(
            target=self._run_more_info_lookup,
            args=(article, cancellation),
            name="newsr-more-info",
            daemon=True,
        )
        self._more_info_thread.start()

    def _run_more_info_lookup(self, article: ArticleRecord, cancellation: RefreshCancellation) -> None:
        try:
            original_article_title = article.title
            original_article_text = self._more_info_source_text(article)
            self._schedule_more_info_progress(article, cancellation, "asking configured llm for search query...")
            query = self.llm_client.build_search_query(
                original_article_title,
                original_article_text,
                cancellation,
            ).strip()
            if not query:
                query = original_article_title
            self._schedule_more_info_progress(article, cancellation, "searching DuckDuckGo...")
            results = self.search_client.search(query, cancellation=cancellation)
            if not results:
                more_info = self.ui.text("more_info.body.no_results")
            else:
                self._schedule_more_info_progress(article, cancellation, "asking configured llm to synthesize results...")
                more_info = self.llm_client.synthesize_more_info(
                    original_article_title,
                    original_article_text,
                    results,
                    cancellation,
                )
        except RefreshCancelled:
            return
        except Exception as exc:
            if self.is_mounted:
                self.call_from_thread(self._finish_more_info_error, article.article_id, cancellation, str(exc))
            return
        if self.is_mounted:
            self.call_from_thread(self._finish_more_info_success, article.article_id, cancellation, more_info)

    def _finish_more_info_success(
        self,
        article_id: str,
        cancellation: RefreshCancellation,
        more_info: str,
    ) -> None:
        if cancellation is not self._more_info_cancellation or article_id != self._more_info_article_id:
            return
        self._more_info_thread = None
        self._more_info_cancellation = None
        self._more_info_cache[article_id] = more_info
        self.storage.update_more_info(article_id, more_info)
        self._refresh_article_more_info(article_id, more_info)
        if self._more_info_screen is not None:
            self._more_info_screen.set_loading(False)
            self._more_info_screen.set_status("ready")
            self._more_info_screen.set_content(more_info)

    def _finish_more_info_error(
        self,
        article_id: str,
        cancellation: RefreshCancellation,
        error_text: str,
    ) -> None:
        if cancellation is not self._more_info_cancellation or article_id != self._more_info_article_id:
            return
        self._more_info_thread = None
        self._more_info_cancellation = None
        if self._more_info_screen is not None:
            self._more_info_screen.set_loading(False)
            self._more_info_screen.set_status("failed")
            self._more_info_screen.set_content(self.ui.text("more_info.body.unavailable", error=error_text))

    def _cancel_more_info_lookup(self) -> None:
        cancellation = self._more_info_cancellation
        self._more_info_cancellation = None
        self._more_info_thread = None
        if cancellation is not None:
            cancellation.cancel()

    def _dismiss_more_info_screen(self) -> None:
        screen = self._more_info_screen
        self._more_info_screen = None
        self._more_info_article_id = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass

    def _more_info_loading_text(self, article: ArticleRecord, stage: str) -> str:
        title = article.translated_title or article.title
        return self.ui.text("more_info.body.loading", title=title, stage=self.ui.status(stage))

    @staticmethod
    def _more_info_source_text(article: ArticleRecord) -> str:
        return NewsReaderApp._article_context_source_text(article)

    @staticmethod
    def _article_context_source_text(article: ArticleRecord) -> str:
        return article.source_body[:4000]

    def _persisted_or_cached_more_info(self, article: ArticleRecord) -> str | None:
        cached = self._more_info_cache.get(article.article_id)
        if cached is not None:
            return cached
        return article.more_info

    def _refresh_article_more_info(self, article_id: str, more_info: str) -> None:
        for index, article in enumerate(self.articles):
            if article.article_id != article_id:
                continue
            self.articles[index] = replace(article, more_info=more_info)
            break

    def _schedule_more_info_progress(
        self,
        article: ArticleRecord,
        cancellation: RefreshCancellation,
        stage: str,
    ) -> None:
        if self.is_mounted:
            self.call_from_thread(self._handle_more_info_progress, article, cancellation, stage)

    def _handle_more_info_progress(
        self,
        article: ArticleRecord,
        cancellation: RefreshCancellation,
        stage: str,
    ) -> None:
        if cancellation is not self._more_info_cancellation or article.article_id != self._more_info_article_id:
            return
        self._update_more_info_loading_state(article, stage)

    def _update_more_info_loading_state(self, article: ArticleRecord, stage: str) -> None:
        if self._more_info_screen is None:
            return
        self._more_info_screen.set_loading(True)
        self._more_info_screen.set_status(stage)
        self._more_info_screen.set_content(self._more_info_loading_text(article, stage))
