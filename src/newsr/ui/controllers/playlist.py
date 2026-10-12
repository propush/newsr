from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import TYPE_CHECKING

from textual.app import ScreenStackError

from ...domain import ArticleRecord, PlaylistItem, ReaderState, ViewMode
from ...providers.tts import TTSEngine, build_tts_engine
from ...tts import AudioOutput, MiniaudioOutput, PlannedItem, PlaybackRunner, body_language, build_item_script
from ..screens import ConfirmDialogScreen
from ..screens.playlist import PlaylistRow, PlaylistScreen
from .article_rendering import article_text, article_title, provider_display_names, truncate_cells

if TYPE_CHECKING:
    from ...config.models import TTSConfig
    from ..app import NewsReaderApp

OutputFactory = Callable[[], AudioOutput]
EngineFactory = Callable[["TTSConfig"], TTSEngine]
_OUTPUT_CLOSE_DELAY_SECONDS = 0.5


class PlaylistController:
    def __init__(
        self,
        app: NewsReaderApp,
        *,
        output_factory: OutputFactory = MiniaudioOutput,
        engine_factory: EngineFactory | None = None,
    ) -> None:
        self._app = app
        self._output_factory = output_factory
        self._engine_factory = engine_factory
        self._items: list[PlaylistItem] = []
        self._runner: PlaybackRunner | None = None
        self._output: AudioOutput | None = None
        self._engine: TTSEngine | None = None
        self._engine_lock = Lock()
        self._current: PlannedItem | None = None
        self._current_title = ""
        self._current_provider = ""
        self._paused = False
        self._buffering = False
        self._error: str | None = None
        self._screen: PlaylistScreen | None = None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def items(self) -> list[PlaylistItem]:
        return list(self._items)

    @property
    def is_running(self) -> bool:
        return self._runner is not None

    @property
    def is_playing(self) -> bool:
        return self._runner is not None and not self._paused

    def load(self) -> None:
        self._items = self._app.storage.load_playlist()

    # ------------------------------------------------------------------
    # Queue editing
    # ------------------------------------------------------------------

    def add_current(self) -> None:
        if not self._can_add():
            return
        article = self._app._navigation.current_article
        if article is None:
            return
        self._append([article])

    def add_rest_of_scope(self) -> None:
        if not self._can_add():
            return
        nav = self._app._navigation
        if not nav.articles:
            return
        self._append(nav.articles[nav.current_index:])

    def remove(self, article_id: str) -> None:
        index = self._index_of(article_id)
        if index is None:
            return
        self._items.pop(index)
        self._save()
        if self._runner is not None and self._current is not None and self._current.article_id == article_id:
            self._runner.skip()
        self._refresh()

    def play_now(self, article_id: str) -> None:
        index = self._index_of(article_id)
        if index is None:
            return
        if index > 0:
            self._items.insert(0, self._items.pop(index))
            self._save()
        if self._runner is None:
            self._start()
            return
        self._resume_output()
        if index > 0 or self._current is None or self._current.article_id != article_id:
            self._runner.restart_item()
        self._refresh()

    def request_clear(self) -> None:
        self._app.push_screen(
            ConfirmDialogScreen(
                self._app.ui,
                title=self._app.ui.text("playlist.clear.title"),
                body=self._app.ui.text("playlist.clear.body", count=len(self._items)),
                confirm_label=self._app.ui.text("playlist.clear.confirm"),
                cancel_label=self._app.ui.text("playlist.clear.cancel"),
            ),
            callback=lambda confirmed: self.clear() if confirmed else None,
        )

    def clear(self) -> None:
        self._stop_runner()
        self._items = []
        self._error = None
        self._save()
        self._close_output_later()
        self._refresh()

    # ------------------------------------------------------------------
    # Playback controls
    # ------------------------------------------------------------------

    def toggle_play(self) -> None:
        if self._runner is None:
            if not self._items:
                self._set_app_status(self._app.ui.text("playlist.status.empty"))
                return
            self._start()
            return
        output = self._output
        if output is None:
            return
        if self._paused:
            self._resume_output()
        else:
            output.pause()
            self._paused = True
        self._refresh()

    def skip(self) -> None:
        if self._runner is not None:
            self._runner.skip()
            return
        if self._items:
            self._items.pop(0)
            self._error = None
            self._save()
            self._refresh()

    def restart_item(self) -> None:
        if self._runner is not None:
            self._resume_output()
            self._runner.restart_item()
            self._refresh()

    def cancel(self) -> None:
        self._stop_runner()
        output = self._output
        self._output = None
        if output is not None:
            output.close()

    # ------------------------------------------------------------------
    # Playlist screen
    # ------------------------------------------------------------------

    def show_screen(self) -> None:
        if self._screen is not None:
            return
        screen = PlaylistScreen(
            self._app.ui,
            self._screen_rows(),
            self._screen_header(),
            provider_display_names(self._app.storage),
        )
        self._screen = screen
        self._app.push_screen(screen, callback=lambda _result: self._screen_closed(screen))

    def _screen_closed(self, screen: PlaylistScreen) -> None:
        if self._screen is screen:
            self._screen = None

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def status_text(self, max_cells: int) -> str:
        ui = self._app.ui
        if self._error is not None:
            text = ui.text("playlist.status.error", error=self._error)
        elif self._runner is not None and self._current is not None:
            if self._paused:
                key = "playlist.status.paused"
            elif self._buffering:
                key = "playlist.status.buffering"
            else:
                key = "playlist.status.playing"
            text = ui.text(
                key,
                title=self._current_title,
                provider=self._current_provider,
                count=len(self._items),
            )
        elif self._runner is not None:
            text = ui.text("playlist.status.starting", count=len(self._items))
        elif self._items:
            text = ui.text("playlist.status.queued", count=len(self._items))
        else:
            return ""
        return truncate_cells(text, max(1, max_cells))

    # ------------------------------------------------------------------
    # PlaybackHost callbacks (UI thread)
    # ------------------------------------------------------------------

    def start_next_item(self, runner: PlaybackRunner) -> PlannedItem | None:
        if runner is not self._runner:
            return None
        while self._items:
            head = self._items[0]
            planned = self._plan(head, mark_read=True)
            if planned is not None:
                self._current = planned
                self._error = None
                self._refresh()
                return planned
            self._items.pop(0)
            self._save()
        self._current = None
        return None

    def peek_next_item(self, runner: PlaybackRunner, after_article_id: str) -> PlannedItem | None:
        if runner is not self._runner:
            return None
        index = self._index_of(after_article_id)
        if index is None or index + 1 >= len(self._items):
            return None
        return self._plan(self._items[index + 1], mark_read=False)

    def item_finished(self, runner: PlaybackRunner, article_id: str) -> None:
        if runner is not self._runner:
            return
        index = self._index_of(article_id)
        if index is not None:
            self._items.pop(index)
            self._save()
        self._current = None
        self._refresh()

    def buffering_changed(self, runner: PlaybackRunner, buffering: bool) -> None:
        if runner is not self._runner:
            return
        self._buffering = buffering
        self._refresh(rows=False)

    def playback_failed(self, runner: PlaybackRunner, article_id: str | None, message: str) -> None:
        if runner is not self._runner:
            return
        self._runner = None
        self._current = None
        self._paused = False
        self._buffering = False
        self._error = message
        self._refresh()

    def playback_finished(self, runner: PlaybackRunner) -> None:
        if runner is not self._runner:
            return
        self._runner = None
        self._current = None
        self._paused = False
        self._buffering = False
        self._set_app_status(self._app.ui.text("playlist.status.finished"))
        self._close_output_later()
        self._refresh()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _can_add(self) -> bool:
        return not self._app.provider_home_open and not self._app._brief.article_open

    def _append(self, articles: list[ArticleRecord]) -> None:
        scope_id = self._app._provider_home.active_scope_id
        queued = {item.article_id for item in self._items}
        added = [
            PlaylistItem(article_id=article.article_id, scope_id=scope_id)
            for article in articles
            if article.article_id not in queued
        ]
        self._items.extend(added)
        self._save()
        self._set_app_status(self._app.ui.text("playlist.status.added", added=len(added), total=len(self._items)))
        self._refresh()

    def _start(self) -> None:
        self._error = None
        self._paused = False
        self._buffering = False
        if self._output is None:
            self._output = self._output_factory()
        self._output.resume()
        runner = PlaybackRunner(
            host=self,
            engine_provider=self._engine_instance,
            output=self._output,
            dispatch=self._app.call_from_thread,
        )
        self._runner = runner
        runner.start()
        self._refresh()

    def _stop_runner(self) -> None:
        runner = self._runner
        self._runner = None
        self._current = None
        self._paused = False
        self._buffering = False
        if runner is not None:
            runner.stop()

    def _resume_output(self) -> None:
        if self._output is not None:
            self._output.resume()
        self._paused = False

    def _engine_instance(self) -> TTSEngine:
        with self._engine_lock:
            if self._engine is None:
                if self._engine_factory is None:
                    self._engine = build_tts_engine(self._app.config.tts, llm=self._app.llm_client)
                else:
                    self._engine = self._engine_factory(self._app.config.tts)
            return self._engine

    def _close_output_later(self) -> None:
        def close_if_idle() -> None:
            if self._runner is None and self._output is not None:
                output = self._output
                self._output = None
                output.close()

        try:
            self._app.set_timer(_OUTPUT_CLOSE_DELAY_SECONDS, close_if_idle)
        except RuntimeError:
            close_if_idle()

    def _plan(self, item: PlaylistItem, *, mark_read: bool) -> PlannedItem | None:
        scope_articles = self._app._articles_for_scope(item.scope_id)
        position = next(
            (index for index, article in enumerate(scope_articles) if article.article_id == item.article_id),
            None,
        )
        if position is None:
            return None
        article = scope_articles[position]
        mode = self._view_mode(item.scope_id)
        if mark_read:
            self._mark_read(item, scope_articles, position)
        config = self._app.config
        provider_name = provider_display_names(self._app.storage).get(article.provider_id, article.provider_id)
        reader_state = ReaderState(article_id=article.article_id, view_mode=mode, scroll_offset=0)
        title = article_title(reader_state, article)
        body = article_text(reader_state, article)
        language = body_language(
            mode,
            f"{title}\n{body}",
            target_language=config.translation.target_language,
            original_language=config.tts.original_language,
        )
        engine_max_chars = self._engine.max_chars if self._engine is not None else 1000
        segments = build_item_script(
            intro=self._app.ui.text(
                "playlist.speech.intro",
                provider=provider_name,
                current=position + 1,
                total=len(scope_articles),
            ),
            intro_language=config.ui.locale,
            title=title,
            body=body,
            body_language=language,
            max_chars=engine_max_chars,
        )
        if mark_read:
            self._current_title = article.translated_title or article.title
            self._current_provider = provider_name
        return PlannedItem(
            article_id=article.article_id,
            scope_id=item.scope_id,
            mode=mode,
            segments=tuple(segments),
        )

    def _view_mode(self, scope_id: str) -> ViewMode:
        if scope_id == self._app._provider_home.active_scope_id:
            return self._app.reader_state.view_mode
        return self._app.storage.load_reader_state(scope_id).view_mode

    def _mark_read(self, item: PlaylistItem, scope_articles: list[ArticleRecord], position: int) -> None:
        if item.scope_id == self._app._provider_home.active_scope_id:
            self._app._navigation.advance_to(item.article_id)
            return
        state = self._app.storage.load_reader_state(item.scope_id)
        current = next(
            (index for index, article in enumerate(scope_articles) if article.article_id == state.article_id),
            -1,
        )
        if position <= current:
            return
        state.article_id = item.article_id
        state.scroll_offset = 0
        self._app.storage.save_reader_state(item.scope_id, state)
        if self._app.provider_home_open:
            self._app._provider_home.refresh_rows()

    def _index_of(self, article_id: str) -> int | None:
        for index, item in enumerate(self._items):
            if item.article_id == article_id:
                return index
        return None

    def _save(self) -> None:
        self._app.storage.save_playlist(self._items)

    def _set_app_status(self, text: str) -> None:
        self._app._refresh.set_status_text(text, busy=False, hold_seconds=2.0)
        self._app.refresh_view()

    def _refresh(self, *, rows: bool = True) -> None:
        screen = self._screen
        if screen is not None:
            try:
                if rows:
                    screen.update_rows(self._screen_rows(), self._screen_header())
                else:
                    screen.update_header(self._screen_header())
            except ScreenStackError:
                pass
        self._app.refresh_view()

    def _screen_rows(self) -> list[PlaylistRow]:
        rows: list[PlaylistRow] = []
        for index, item in enumerate(self._items):
            article = self._app.storage.get_article(item.article_id)
            if article is None:
                continue
            rows.append(PlaylistRow(article=article, marker=self._marker(index, item)))
        return rows

    def _marker(self, index: int, item: PlaylistItem) -> str:
        if index != 0 or self._current is None or self._current.article_id != item.article_id:
            return ""
        return "‖" if self._paused else "▶"

    def _screen_header(self) -> str:
        ui = self._app.ui
        if self._runner is None:
            state = ui.text("playlist.state.stopped")
        elif self._paused:
            state = ui.text("playlist.state.paused")
        else:
            state = ui.text("playlist.state.playing")
        return ui.text("playlist.header", count=len(self._items), state=state)
