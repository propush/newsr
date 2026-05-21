from __future__ import annotations

from threading import Thread
from typing import TYPE_CHECKING

from textual.app import ScreenStackError

from ...brief import BriefArticle, BriefOptions, BriefProgress, BriefResult, BriefService
from ...cancellation import RefreshCancellation, RefreshCancelled
from ...domain import ArticleRecord
from ...domain.reader import ReaderState
from ..screens import BriefArticleJumpScreen, BriefReaderScreen, BriefScreen

if TYPE_CHECKING:
    from ..app import NewsReaderApp


class BriefController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._screen: BriefScreen | None = None
        self._reader_screen: BriefReaderScreen | None = None
        self._jump_screen: BriefArticleJumpScreen | None = None
        self._thread: Thread | None = None
        self._cancellation: RefreshCancellation | None = None
        self._report: str | None = None
        self._articles: list[BriefArticle] = []
        self._reader_scroll_offset = 0
        self._active_article: ArticleRecord | None = None
        self._active_article_number: int | None = None
        self._active_reader_state: ReaderState | None = None

    @property
    def article_open(self) -> bool:
        return self._active_article is not None

    @property
    def active_article(self) -> ArticleRecord | None:
        return self._active_article

    @property
    def active_reader_state(self) -> ReaderState | None:
        return self._active_reader_state

    @property
    def active_article_position(self) -> tuple[int, int] | None:
        if self._active_article_number is None:
            return None
        return (self._active_article_number - 1, len(self._articles))

    def show(self) -> None:
        if not self._app.provider_home_open:
            return
        if self._screen is not None:
            return
        if self._reader_screen is not None:
            return
        if self.article_open:
            return
        screen = BriefScreen(self._app.ui)
        self._screen = screen
        self._app.push_screen(screen)

    def generate(self) -> None:
        screen = self._screen
        if screen is None or self._cancellation is not None:
            return
        options = screen.current_options()
        screen.set_generating(True)
        screen.set_content(self._app.ui.text("brief.body.starting"))
        cancellation = RefreshCancellation()
        self._cancellation = cancellation
        self._thread = Thread(
            target=self._run_generate,
            args=(options, cancellation),
            name="newsr-brief",
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        if self._cancellation is not None:
            self.cancel()
            if self._screen is not None:
                self._screen.set_generating(False)
                self._screen.set_content(self._app.ui.text("brief.body.cancelled"))
            return
        self._dismiss_screen()
        self._dismiss_reader_screen()
        self._dismiss_jump_screen()
        self._close_article_view()

    def close_reader(self) -> None:
        self._dismiss_reader_screen()

    def show_jump(self, initial_value: str) -> None:
        if self._reader_screen is None or not self._articles or self._jump_screen is not None:
            return
        screen = BriefArticleJumpScreen(
            self._app.ui,
            initial_value=initial_value,
            max_number=len(self._articles),
        )
        self._jump_screen = screen
        self._app.push_screen(screen)

    def close_jump(self, *, cancelled: bool) -> None:
        self._dismiss_jump_screen()
        if cancelled:
            self._app.restore_navigation_focus()

    def open_article_number(self, number: int) -> None:
        self._dismiss_jump_screen()
        brief_article = self._brief_article_by_number(number)
        if brief_article is None:
            self._app._refresh.set_status_text(
                self._app.ui.text("brief_jump.status.not_found"),
                busy=False,
                hold_seconds=1.0,
            )
            self._app.refresh_view()
            self._app.restore_navigation_focus()
            return
        article = self._app.storage.get_article(brief_article.article_id)
        if article is None or article.translation_status != "done" or article.translated_body is None:
            self._app._refresh.set_status_text(
                self._app.ui.text("brief_jump.status.not_found"),
                busy=False,
                hold_seconds=1.0,
            )
            self._app.refresh_view()
            self._app.restore_navigation_focus()
            return
        self._reader_scroll_offset = self._reader_screen.report_scroll_offset() if self._reader_screen is not None else 0
        self._dismiss_reader_screen(restore_focus=False)
        self._active_article = article
        self._active_article_number = number
        self._active_reader_state = ReaderState(
            article_id=article.article_id,
            view_mode=self._app.reader_state.view_mode,
            scroll_offset=0,
        )
        self._app._set_provider_home_footer_bindings(provider_home_open=False)
        self._app._provider_home._notify_bindings_changed()
        self._app._navigation.invalidate_render_cache()
        self._app.refresh_view()
        self._app.restore_reader_focus()

    def return_to_reader(self) -> None:
        if not self.article_open:
            return
        self._close_article_view()
        if self._report is not None:
            self._show_reader(self._report, restore_scroll_offset=self._reader_scroll_offset)
        self._app._set_provider_home_footer_bindings(provider_home_open=True)
        self._app._provider_home._notify_bindings_changed()
        self._app._navigation.invalidate_render_cache()
        self._app.refresh_view()

    def update_active_article(self, article: ArticleRecord) -> None:
        if self._active_article is None or self._active_article.article_id != article.article_id:
            return
        self._active_article = article

    def cancel(self) -> None:
        cancellation = self._cancellation
        self._cancellation = None
        self._thread = None
        if cancellation is not None:
            cancellation.cancel()

    def _run_generate(self, options: BriefOptions, cancellation: RefreshCancellation) -> None:
        service = BriefService(self._app.config, self._app.storage, self._app.llm_client)
        try:
            result = service.generate(
                options,
                cancellation=cancellation,
                on_progress=lambda progress: self._schedule_progress(cancellation, progress),
            )
        except RefreshCancelled:
            return
        except Exception as exc:
            if self._app.is_mounted:
                self._app.call_from_thread(self._finish_error, cancellation, str(exc))
            return
        if self._app.is_mounted:
            self._app.call_from_thread(self._finish_success, cancellation, result)

    def _finish_success(self, cancellation: RefreshCancellation, result: BriefResult) -> None:
        if cancellation is not self._cancellation:
            return
        self._thread = None
        self._cancellation = None
        self._report = result.report
        self._articles = list(result.articles)
        self._reader_scroll_offset = 0
        if self._screen is not None:
            self._screen.set_generating(False)
        self._dismiss_screen(restore_focus=False)
        self._sync_active_reader_state(result.provider_ids)
        self._show_reader(result.report)
        self._app._provider_home.refresh_rows()
        self._app.refresh_view()

    def _finish_error(self, cancellation: RefreshCancellation, error_text: str) -> None:
        if cancellation is not self._cancellation:
            return
        self._thread = None
        self._cancellation = None
        if self._screen is not None:
            self._screen.set_error(error_text)

    def _schedule_progress(self, cancellation: RefreshCancellation, progress: BriefProgress) -> None:
        if self._app.is_mounted:
            self._app.call_from_thread(self._handle_progress, cancellation, progress)

    def _handle_progress(self, cancellation: RefreshCancellation, progress: BriefProgress) -> None:
        if cancellation is not self._cancellation or self._screen is None:
            return
        self._screen.set_progress(progress)

    def _show_reader(self, report: str, *, restore_scroll_offset: int = 0) -> None:
        if self._reader_screen is not None:
            return
        screen = BriefReaderScreen(self._app.ui, report, article_count=len(self._articles))
        self._reader_screen = screen
        self._app.push_screen(screen)
        if restore_scroll_offset > 0:
            self._app.call_after_refresh(screen.restore_scroll_offset, restore_scroll_offset)

    def _sync_active_reader_state(self, provider_ids: list[str]) -> None:
        if self._app._provider_home.active_scope_id not in provider_ids:
            return
        self._app.reader_state = self._app.storage.load_reader_state(
            self._app._provider_home.active_scope_id
        )
        self._app.load_articles(
            preferred_article_id=self._app.reader_state.article_id,
            fallback_to_current_article=False,
        )

    def _dismiss_screen(self, *, restore_focus: bool = True) -> None:
        screen = self._screen
        self._screen = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass
        if restore_focus:
            self._app.restore_navigation_focus()

    def _dismiss_reader_screen(self, *, restore_focus: bool = True) -> None:
        screen = self._reader_screen
        self._reader_screen = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass
        if restore_focus:
            self._app.restore_navigation_focus()

    def _dismiss_jump_screen(self) -> None:
        screen = self._jump_screen
        self._jump_screen = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass

    def _close_article_view(self) -> None:
        self._active_article = None
        self._active_article_number = None
        self._active_reader_state = None

    def _brief_article_by_number(self, number: int) -> BriefArticle | None:
        for article in self._articles:
            if article.number == number:
                return article
        return None
