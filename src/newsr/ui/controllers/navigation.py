from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ScreenStackError
from textual.containers import VerticalScroll
from textual.css.query import NoMatches

from ...domain import ArticleRecord
from ..screens import OpenLinkConfirmScreen

if TYPE_CHECKING:
    from ...domain.reader import ReaderState
    from ..app import NewsReaderApp


class NavigationController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self.articles: list[ArticleRecord] = []
        self.current_index: int = 0
        self._pending_scroll_restore: bool = False
        self._scroll_restore_attempts_remaining: int = 0
        self._scroll_restore_scheduled: bool = False
        self._state_persisted: bool = False
        self._rendered_header_text: Text | None = None
        self._rendered_body_text: str | None = None
        self._rendered_article_url: str | None = None
        self._rendered_status_text: str | None = None
        self._open_link_confirm_screen: OpenLinkConfirmScreen | None = None
        self._pending_open_link: tuple[str, str] | None = None

    # ------------------------------------------------------------------
    # Article state
    # ------------------------------------------------------------------

    @property
    def current_article(self) -> ArticleRecord | None:
        if not self.articles:
            return None
        return self.articles[self.current_index]

    # ------------------------------------------------------------------
    # Article loading
    # ------------------------------------------------------------------

    def load_articles(
        self,
        *,
        preferred_article_id: str | None = None,
        auto_select_first: bool = False,
        fallback_to_current_article: bool = True,
    ) -> None:
        current_article = self.current_article
        self.articles = self._articles_for_scope(self._app._provider_home.active_scope_id)
        self.current_index = self._resolve_current_index(
            preferred_article_id=preferred_article_id
            or (
                current_article.article_id
                if current_article is not None and fallback_to_current_article
                else None
            ),
            auto_select_first=auto_select_first,
        )
        self._sync_reader_state_after_article_load()
        try:
            self._app.refresh_view()
        except (NoMatches, ScreenStackError):
            pass

    def _articles_for_scope(self, scope_id: str) -> list[ArticleRecord]:
        from .provider_home import ALL_PROVIDERS_SCOPE_ID

        articles = [article for article in self._app.storage.list_articles() if self._article_is_translated(article)]
        if scope_id == ALL_PROVIDERS_SCOPE_ID:
            return articles
        return [article for article in articles if article.provider_id == scope_id]

    @staticmethod
    def _article_is_translated(article: ArticleRecord) -> bool:
        return article.translation_status == "done" and article.translated_body is not None

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
        article_id = preferred_article_id or self._app.reader_state.article_id
        if article_id is None:
            return 0
        for index, article in enumerate(self.articles):
            if article.article_id == article_id:
                return index
        return 0

    def _sync_reader_state_after_article_load(self) -> None:
        article = self.current_article
        self._app.reader_state.article_id = article.article_id if article else None
        if article is None:
            self._app.reader_state.scroll_offset = 0

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def persist_reader_state(self) -> None:
        if self._state_persisted:
            return
        self._app.storage.save_reader_state(
            self._app._provider_home.active_scope_id, self.capture_reader_state(),
        )
        self._state_persisted = True

    def save_reader_state_now(self) -> None:
        self._state_persisted = False
        self.persist_reader_state()

    def capture_reader_state(self) -> ReaderState:
        article = self.current_article
        self._app.reader_state.article_id = article.article_id if article else None
        try:
            pane = self._app.query_one("#article-pane", VerticalScroll)
            self._app.reader_state.scroll_offset = int(pane.scroll_y)
        except (NoMatches, ScreenStackError):
            pass
        return self._app.reader_state

    def queue_scroll_restore(self) -> None:
        self._pending_scroll_restore = True
        self._scroll_restore_attempts_remaining = 20
        self.schedule_scroll_restore()

    def schedule_scroll_restore(self) -> None:
        if not self._pending_scroll_restore or self._scroll_restore_scheduled:
            return
        self._scroll_restore_scheduled = True
        self._app.set_timer(0.01, self._run_scheduled_scroll_restore)

    def _run_scheduled_scroll_restore(self) -> None:
        self._scroll_restore_scheduled = False
        self.restore_scroll_if_needed()

    def restore_scroll_if_needed(self) -> None:
        if not self._pending_scroll_restore:
            return
        if self._app.provider_home_open:
            self.schedule_scroll_restore()
            return
        try:
            pane = self._app.query_one("#article-pane", VerticalScroll)
        except (NoMatches, ScreenStackError):
            self.schedule_scroll_restore()
            return
        requested_offset = max(0, self._app.reader_state.scroll_offset)
        self._scroll_restore_attempts_remaining = max(0, self._scroll_restore_attempts_remaining - 1)
        max_offset = int(pane.max_scroll_y)
        if requested_offset > 0 and max_offset == 0 and self._scroll_restore_attempts_remaining > 0:
            self.schedule_scroll_restore()
            return
        target_offset = min(requested_offset, max_offset)
        pane.scroll_to(y=target_offset, animate=False)
        if self._scroll_restore_attempts_remaining > 0:
            self.schedule_scroll_restore()
            return
        self._pending_scroll_restore = False
        self._scroll_restore_attempts_remaining = 0
        self._scroll_restore_scheduled = False

    # ------------------------------------------------------------------
    # Render cache
    # ------------------------------------------------------------------

    def invalidate_render_cache(self) -> None:
        self._rendered_article_url = None
        self._rendered_status_text = None
        if self._app.provider_home_open:
            self._app._provider_home.refresh_rows()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def previous(self) -> None:
        if self._app.provider_home_open or self._app._article_qa.is_active:
            return
        if self.current_index == 0:
            return
        self._app.close_more_info()
        self.current_index -= 1
        self.reset_scroll()
        self._app.refresh_view()
        self.save_reader_state_now()

    def next(self) -> None:
        if self._app.provider_home_open or self._app._article_qa.is_active:
            return
        if not self.articles:
            return
        if self.current_index >= len(self.articles) - 1:
            self.save_reader_state_now()
            self._app.show_provider_home()
            return
        self._app.close_more_info()
        self.current_index += 1
        self.reset_scroll()
        self._app.refresh_view()
        self.save_reader_state_now()

    def toggle_summary(self) -> None:
        from ...domain.reader import ViewMode

        if self._app.provider_home_open:
            return
        article = self.current_article
        if article is None or not article.summary:
            return
        self._app.reader_state.view_mode = (
            ViewMode.SUMMARY if self._app.reader_state.view_mode == ViewMode.FULL else ViewMode.FULL
        )
        self._app.refresh_view()
        self.save_reader_state_now()

    def scroll_up(self) -> None:
        if self._app.provider_home_open:
            self._app._provider_home.move_cursor(-1)
            return
        self._app.query_one("#article-pane", VerticalScroll).scroll_up(animate=False)

    def scroll_down(self) -> None:
        if self._app.provider_home_open:
            self._app._provider_home.move_cursor(1)
            return
        self._app.query_one("#article-pane", VerticalScroll).scroll_down(animate=False)

    def page_up(self) -> None:
        if self._app.provider_home_open:
            self._app.page_provider_home(-1)
            return
        self._app.query_one("#article-pane", VerticalScroll).scroll_page_up(animate=False)

    def page_down(self) -> None:
        if self._app.provider_home_open:
            self._app.page_provider_home(1)
            return
        self._app.query_one("#article-pane", VerticalScroll).scroll_page_down(animate=False)

    def space_down(self) -> None:
        if self._app.provider_home_open:
            return
        pane = self._app.query_one("#article-pane", VerticalScroll)
        if pane.scroll_y >= pane.max_scroll_y:
            self.next()
            return
        pane.scroll_page_down(animate=False)

    def open_article(self) -> None:
        if self._app.provider_home_open:
            return
        article = self.current_article
        if article is None:
            return
        self.request_open_link(article.translated_title or article.title, article.url)

    def open_external_url(self, url: str) -> None:
        from ...providers.search.duckduckgo import normalize_result_url

        normalized_url = normalize_result_url(url)
        try:
            opened = webbrowser.open(normalized_url, new=2)
        except Exception as exc:
            self._app._refresh.set_status_text(
                self._app.ui.text("app.status.browser_open_failed", error=exc), busy=False, hold_seconds=1.0
            )
        else:
            self._app._refresh.set_status_text(
                self._app.ui.text("app.status.browser_opened")
                if opened
                else self._app.ui.text("app.status.browser_not_confirmed"),
                busy=False,
                hold_seconds=1.0,
            )
        self._app.refresh_view()

    def open_by_id(self, article_id: str) -> None:
        if self._app._article_qa.is_active:
            return
        for index, article in enumerate(self.articles):
            if article.article_id != article_id:
                continue
            self._app.close_more_info()
            self.current_index = index
            self.reset_scroll()
            self._app.refresh_view()
            self.save_reader_state_now()
            return

    def reset_scroll(self) -> None:
        self._pending_scroll_restore = False
        self._scroll_restore_attempts_remaining = 0
        self._scroll_restore_scheduled = False
        self._app.reader_state.scroll_offset = 0
        self._app.query_one("#article-pane", VerticalScroll).scroll_to(y=0, animate=False)

    # ------------------------------------------------------------------
    # Link confirmation
    # ------------------------------------------------------------------

    def request_open_link(self, title: str, url: str) -> None:
        from ...providers.search.duckduckgo import normalize_result_url

        normalized_url = normalize_result_url(url)
        self.close_open_link_confirm()
        self._pending_open_link = (title, normalized_url)
        screen = OpenLinkConfirmScreen(self._app.ui, title, normalized_url)
        self._open_link_confirm_screen = screen
        self._app.push_screen(screen)

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
        self._app.call_after_refresh(self._app.set_focus, None)
