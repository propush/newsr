from __future__ import annotations

from dataclasses import replace
from threading import Thread
from typing import TYPE_CHECKING

from ...cancellation import RefreshCancellation, RefreshCancelled
from ..screens import MoreInfoScreen
from . import article_context_source_text

if TYPE_CHECKING:
    from ...domain import ArticleRecord
    from ..app import NewsReaderApp


class MoreInfoController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._cache: dict[str, str] = {}
        self._screen: MoreInfoScreen | None = None
        self._thread: Thread | None = None
        self._cancellation: RefreshCancellation | None = None
        self._article_id: str | None = None

    def refresh(self, *, force_refresh: bool) -> None:
        article = self._app.current_article
        if article is None:
            return
        screen = self._ensure_screen(article)
        cached = self._persisted_or_cached(article)
        if cached is not None and not force_refresh:
            screen.set_loading(False)
            screen.set_status("cached")
            screen.set_content(cached)
            self._cache[article.article_id] = cached
            return
        self._update_loading_state(article, "asking configured llm for search query...")
        self._start_lookup(article)

    def close(self) -> None:
        self._cancel_lookup()
        self._dismiss_screen()

    def cancel(self) -> None:
        self._cancel_lookup()

    def _ensure_screen(self, article: ArticleRecord) -> MoreInfoScreen:
        existing = self._screen
        if existing is not None:
            if self._article_id != article.article_id:
                self.close()
            else:
                existing.article_title = article.translated_title or article.title
                existing.update_header()
                return existing
        screen = MoreInfoScreen(self._app.ui, article.translated_title or article.title)
        self._screen = screen
        self._article_id = article.article_id
        self._app.push_screen(screen)
        return screen

    def _start_lookup(self, article: ArticleRecord) -> None:
        self._cancel_lookup()
        cancellation = RefreshCancellation()
        self._cancellation = cancellation
        self._article_id = article.article_id
        self._thread = Thread(
            target=self._run_lookup,
            args=(article, cancellation),
            name="newsr-more-info",
            daemon=True,
        )
        self._thread.start()

    def _run_lookup(self, article: ArticleRecord, cancellation: RefreshCancellation) -> None:
        try:
            original_article_title = article.title
            original_article_text = article_context_source_text(article)
            self._schedule_progress(article, cancellation, "asking configured llm for search query...")
            query = self._app.llm_client.build_search_query(
                original_article_title,
                original_article_text,
                cancellation,
            ).strip()
            if not query:
                query = original_article_title
            self._schedule_progress(article, cancellation, "searching DuckDuckGo...")
            results = self._app.search_client.search(query, cancellation=cancellation)
            if not results:
                more_info = self._app.ui.text("more_info.body.no_results")
            else:
                self._schedule_progress(article, cancellation, "asking configured llm to synthesize results...")
                more_info = self._app.llm_client.synthesize_more_info(
                    original_article_title,
                    original_article_text,
                    results,
                    cancellation,
                )
        except RefreshCancelled:
            return
        except Exception as exc:
            if self._app.is_mounted:
                self._app.call_from_thread(self._finish_error, article.article_id, cancellation, str(exc))
            return
        if self._app.is_mounted:
            self._app.call_from_thread(self._finish_success, article.article_id, cancellation, more_info)

    def _finish_success(
        self,
        article_id: str,
        cancellation: RefreshCancellation,
        more_info: str,
    ) -> None:
        if cancellation is not self._cancellation or article_id != self._article_id:
            return
        self._thread = None
        self._cancellation = None
        self._cache[article_id] = more_info
        self._app.storage.update_more_info(article_id, more_info)
        self._refresh_article_more_info(article_id, more_info)
        if self._screen is not None:
            self._screen.set_loading(False)
            self._screen.set_status("ready")
            self._screen.set_content(more_info)

    def _finish_error(
        self,
        article_id: str,
        cancellation: RefreshCancellation,
        error_text: str,
    ) -> None:
        if cancellation is not self._cancellation or article_id != self._article_id:
            return
        self._thread = None
        self._cancellation = None
        if self._screen is not None:
            self._screen.set_loading(False)
            self._screen.set_status("failed")
            self._screen.set_content(self._app.ui.text("more_info.body.unavailable", error=error_text))

    def _cancel_lookup(self) -> None:
        cancellation = self._cancellation
        self._cancellation = None
        self._thread = None
        if cancellation is not None:
            cancellation.cancel()

    def _dismiss_screen(self) -> None:
        from textual.app import ScreenStackError

        screen = self._screen
        self._screen = None
        self._article_id = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass

    def _loading_text(self, article: ArticleRecord, stage: str) -> str:
        title = article.translated_title or article.title
        return self._app.ui.text("more_info.body.loading", title=title, stage=self._app.ui.status(stage))

    def _persisted_or_cached(self, article: ArticleRecord) -> str | None:
        cached = self._cache.get(article.article_id)
        if cached is not None:
            return cached
        return article.more_info

    def _refresh_article_more_info(self, article_id: str, more_info: str) -> None:
        for index, article in enumerate(self._app.articles):
            if article.article_id != article_id:
                continue
            self._app.articles[index] = replace(article, more_info=more_info)
            break

    def _schedule_progress(
        self,
        article: ArticleRecord,
        cancellation: RefreshCancellation,
        stage: str,
    ) -> None:
        if self._app.is_mounted:
            self._app.call_from_thread(self._handle_progress, article, cancellation, stage)

    def _handle_progress(
        self,
        article: ArticleRecord,
        cancellation: RefreshCancellation,
        stage: str,
    ) -> None:
        if cancellation is not self._cancellation or article.article_id != self._article_id:
            return
        self._update_loading_state(article, stage)

    def _update_loading_state(self, article: ArticleRecord, stage: str) -> None:
        if self._screen is None:
            return
        self._screen.set_loading(True)
        self._screen.set_status(stage)
        self._screen.set_content(self._loading_text(article, stage))
