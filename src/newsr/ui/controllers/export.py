from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ScreenStackError

from ...export import ExportAction
from ..screens import ExportScreen

if TYPE_CHECKING:
    from ..app import NewsReaderApp


class ExportController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._screen: ExportScreen | None = None

    def export_current(self) -> None:
        from .article_rendering import view_mode_label

        if self._app.provider_home_open:
            return
        if len(self._app.screen_stack) > 1:
            return
        article = self._app.current_article
        if article is None:
            self._app._refresh.set_status_text(
                self._app.ui.text("app.status.no_article_to_export"), busy=False, hold_seconds=1.0,
            )
            self._app.refresh_view()
            return
        if self._screen is not None:
            return
        self._screen = ExportScreen(
            self._app.ui,
            article.translated_title or article.title,
            view_mode_label(self._app.ui, self._app.reader_state, article),
        )
        self._app.push_screen(self._screen)

    def run_export(self, action: ExportAction) -> None:
        article = self._app.current_article
        if article is None:
            self.close()
            self._app._refresh.set_status_text(
                self._app.ui.text("app.status.no_article_to_export"), busy=False, hold_seconds=1.0,
            )
            self._app.refresh_view()
            return
        result = self._app.export_service.export(
            action,
            article=article,
            view_mode=self._app.reader_state.view_mode,
            theme=self._app.get_theme(self._app.theme),
            config=self._app.config,
        )
        self._app._refresh.set_status_text(result.message, busy=False, hold_seconds=1.2)
        if result.success:
            self.close()
        self._app.refresh_view()

    def close(self) -> None:
        screen = self._screen
        self._screen = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass
