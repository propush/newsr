from __future__ import annotations

from dataclasses import replace
from threading import Thread
from typing import TYPE_CHECKING

from ...cancellation import RefreshCancellation, RefreshCancelled
from ...domain import normalize_article_categories

if TYPE_CHECKING:
    from ...domain import ArticleRecord
    from ..app import NewsReaderApp


class ArticleCategorizationController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._thread: Thread | None = None
        self._cancellation: RefreshCancellation | None = None
        self._article_id: str | None = None

    def categorize_current(self) -> None:
        article = self._app.current_article
        if self._app.provider_home_open or article is None or self._cancellation is not None:
            return
        cancellation = RefreshCancellation()
        self._cancellation = cancellation
        self._article_id = article.article_id
        self._app._refresh.set_status_text(
            self._app.ui.text("app.status.classifying_current_article"),
            busy=True,
        )
        self._app.refresh_view()
        self._thread = Thread(
            target=self._run_request,
            args=(article, cancellation),
            name="newsr-article-categorization",
            daemon=True,
        )
        self._thread.start()

    def cancel(self) -> None:
        cancellation = self._cancellation
        self._cancellation = None
        self._thread = None
        self._article_id = None
        if cancellation is not None:
            cancellation.cancel()

    def _run_request(self, article: ArticleRecord, cancellation: RefreshCancellation) -> None:
        try:
            categories = self._app.llm_client.classify_article_categories(
                article.title,
                article.source_body,
                cancellation,
            )
        except RefreshCancelled:
            return
        except Exception as exc:
            if self._app.is_mounted:
                self._app.call_from_thread(
                    self._finish_error,
                    article.article_id,
                    cancellation,
                    str(exc),
                )
            return
        if self._app.is_mounted:
            self._app.call_from_thread(
                self._finish_success,
                article.article_id,
                cancellation,
                categories,
            )

    def _finish_success(
        self,
        article_id: str,
        cancellation: RefreshCancellation,
        categories: tuple[str, ...],
    ) -> None:
        if cancellation is not self._cancellation or article_id != self._article_id:
            return
        self._thread = None
        self._cancellation = None
        self._article_id = None
        normalized_categories = normalize_article_categories(categories)
        self._app.storage.replace_categories(article_id, normalized_categories)
        self._refresh_article(article_id, normalized_categories)
        self._app._refresh.set_status_text(
            self._app.ui.text("app.status.article_categories_updated"),
            busy=False,
            hold_seconds=2.0,
        )
        self._app.refresh_view()

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
        self._article_id = None
        self._app._refresh.set_status_text(
            self._app.ui.text("app.status.article_categories_update_failed", error=error_text),
            busy=False,
            hold_seconds=3.0,
        )
        self._app.refresh_view()

    def _refresh_article(self, article_id: str, categories: tuple[str, ...]) -> None:
        for index, article in enumerate(self._app.articles):
            if article.article_id != article_id:
                continue
            self._app.articles[index] = replace(article, categories=categories)
            break
