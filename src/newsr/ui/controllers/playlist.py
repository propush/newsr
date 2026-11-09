from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import TYPE_CHECKING

from textual.app import ScreenStackError
from textual.timer import Timer

from ...domain import ArticleRecord, PlaylistItem, ViewMode
from ...providers.tts import TTSEngine, build_tts_engine
from ...providers.tts.base import LOGGER, PreparingTTSEngine, configure_tts_logger
from ...tts import (
    AudioOutput,
    MediaCommand,
    MediaControls,
    MiniaudioOutput,
    NowPlaying,
    NullMediaControls,
    PlannedItem,
    PlaybackRunner,
    PlaybackStatus,
    SpeechPreparer,
    build_media_controls,
)
from ...tts.media_controls.base import ALBUM_TITLE
from ..screens import ConfirmDialogScreen
from ..screens.playlist import PlaylistRow, PlaylistScreen
from .article_rendering import provider_display_names, truncate_cells
from .playlist_script import article_segments, preparation_texts

if TYPE_CHECKING:
    from ...config.models import TTSConfig
    from ..app import NewsReaderApp

OutputFactory = Callable[[], AudioOutput]
EngineFactory = Callable[["TTSConfig"], TTSEngine]
MediaControlsFactory = Callable[[bool], MediaControls]
_OUTPUT_CLOSE_DELAY_SECONDS = 0.5
_HISTORY_LIMIT = 50


class PlaylistController:
    def __init__(
        self,
        app: NewsReaderApp,
        *,
        output_factory: OutputFactory = MiniaudioOutput,
        engine_factory: EngineFactory | None = None,
        media_controls_factory: MediaControlsFactory = build_media_controls,
    ) -> None:
        self._app = app
        self._output_factory = output_factory
        self._engine_factory = engine_factory
        self._media_controls_factory = media_controls_factory
        self._items: list[PlaylistItem] = []
        self._history: list[PlaylistItem] = []
        self._runner: PlaybackRunner | None = None
        self._output: AudioOutput | None = None
        self._engine: TTSEngine | None = None
        self._engine_lock = Lock()
        self._preparer: SpeechPreparer | None = None
        self._current: PlannedItem | None = None
        self._current_title = ""
        self._current_provider = ""
        self._paused = False
        self._buffering = False
        self._error: str | None = None
        self._screen: PlaylistScreen | None = None
        self._media: MediaControls | None = None
        self._media_state: NowPlaying | None = None
        self._media_timer: Timer | None = None

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

    @property
    def preparing_count(self) -> int:
        return self._preparer.pending_count if self._preparer is not None else 0

    def load(self) -> None:
        self._items = self._app.storage.load_playlist()

    # ------------------------------------------------------------------
    # Speech preparation
    # ------------------------------------------------------------------

    def prepare_queued(self) -> None:
        """Prepare a restored playlist; articles whose preparation finished earlier cost almost nothing."""
        self._prepare(self._items)

    def article_updated(self, article_id: str) -> None:
        """Prepare a queued article again after the refresh changed its text, such as a new summary."""
        self._prepare([item for item in self._items if item.article_id == article_id])

    # ------------------------------------------------------------------
    # Queue editing
    # ------------------------------------------------------------------

    def add_current(self) -> None:
        if not self._can_add():
            return
        article = self._app._navigation.current_article
        if article is None:
            return
        self.add_items(self._active_scope_items([article]))

    def add_rest_of_scope(self) -> None:
        if not self._can_add():
            return
        nav = self._app._navigation
        if not nav.articles:
            return
        self.add_items(self._active_scope_items(nav.articles[nav.current_index:]))

    def add_all_unread(self) -> None:
        """Queue the unread articles of every enabled provider, each under its own provider scope."""
        articles = self._app._provider_home.unread_articles()
        self.add_items(
            [PlaylistItem(article_id=article.article_id, scope_id=article.provider_id) for article in articles]
        )

    def add_items(self, items: list[PlaylistItem], *, notify: bool = False) -> None:
        queued = {item.article_id for item in self._items}
        added: list[PlaylistItem] = []
        for item in items:
            if item.article_id in queued:
                continue
            queued.add(item.article_id)
            added.append(item)
        self._items.extend(added)
        self._save()
        self._prepare(added)
        text = self._app.ui.text("playlist.status.added", added=len(added), total=len(self._items))
        self._set_app_status(text)
        if notify:
            self._app.notify(text)
        self._refresh()

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
        self._history = []
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

    def previous(self) -> None:
        """Restart the current article, or return to the previous one while its intro plays."""
        runner = self._runner
        if runner is None:
            return
        if runner.current_segment_index == 0 and self._history:
            item = self._history.pop()
            index = self._index_of(item.article_id)
            if index is not None:
                self._items.pop(index)
            self._items.insert(0, item)
            self._save()
        self._resume_output()
        runner.restart_item()
        self._refresh()

    def seek(self, delta: int) -> None:
        if self._runner is not None:
            self._runner.seek_segment(delta)

    def cancel(self) -> None:
        self._stop_runner()
        preparer = self._preparer
        self._preparer = None
        if preparer is not None:
            preparer.stop()
        output = self._output
        self._output = None
        if output is not None:
            output.close()
        self._close_media()

    # ------------------------------------------------------------------
    # Operating-system media controls
    # ------------------------------------------------------------------

    def handle_media_command(self, command: MediaCommand) -> None:
        if command is MediaCommand.TOGGLE:
            self.toggle_play()
        elif command is MediaCommand.PLAY:
            if not self.is_playing:
                self.toggle_play()
        elif command in (MediaCommand.PAUSE, MediaCommand.STOP):
            if self.is_playing:
                self.toggle_play()
        elif self._runner is None:
            return
        elif command is MediaCommand.NEXT:
            self.skip()
        elif command is MediaCommand.PREVIOUS:
            self.previous()
        elif command is MediaCommand.SEEK_FORWARD:
            self.seek(1)
        elif command is MediaCommand.SEEK_BACKWARD:
            self.seek(-1)

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
        else:
            if self._runner is not None and self._current is not None:
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
            preparing = self.preparing_count
            if preparing:
                text += ui.text("playlist.status.preparing", count=preparing)
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
            self._history.append(self._items.pop(index))
            del self._history[:-_HISTORY_LIMIT]
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

    def _active_scope_items(self, articles: list[ArticleRecord]) -> list[PlaylistItem]:
        scope_id = self._app._provider_home.active_scope_id
        return [PlaylistItem(article_id=article.article_id, scope_id=scope_id) for article in articles]

    def _start(self) -> None:
        self._error = None
        self._paused = False
        self._buffering = False
        if self._output is None:
            self._output = self._output_factory()
        self._output.resume()
        self._ensure_media()
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

    def _prepare(self, items: list[PlaylistItem]) -> None:
        if not items:
            return
        engine = self._engine_instance()
        if not isinstance(engine, PreparingTTSEngine):
            return
        preparer = self._preparer
        if preparer is None:
            preparer = self._preparer = SpeechPreparer(engine, on_change=self._preparation_changed)
        provider_names = provider_display_names(self._app.storage)
        scopes: dict[str, list[ArticleRecord]] = {}
        for item in items:
            if item.scope_id not in scopes:
                scopes[item.scope_id] = self._app._articles_for_scope(item.scope_id)
            scope_articles = scopes[item.scope_id]
            position = _position(scope_articles, item.article_id)
            if position is None:
                continue
            article = scope_articles[position]
            preparer.submit(
                article.article_id,
                preparation_texts(
                    self._app.ui,
                    self._app.config,
                    article,
                    position=position,
                    total=len(scope_articles),
                    provider_name=provider_names.get(article.provider_id, article.provider_id),
                    max_chars=engine.max_chars,
                ),
            )
        preparer.sync([item.article_id for item in self._items])

    def _preparation_changed(self) -> None:
        """Runs on the preparation thread after each finished article."""
        app = self._app
        if not app.is_mounted:
            return
        loop = getattr(app, "_loop", None)
        if loop is None or loop.is_closed():
            return
        try:
            app.call_from_thread(self._refresh, rows=False)
        except RuntimeError:
            return

    def _ensure_media(self) -> None:
        if self._media is not None:
            return
        media = self._media_controls_factory(self._app.config.tts.media_controls)
        media.start(lambda command: self._app.call_later(self.handle_media_command, command))
        self._media = media

    def _sync_media(self) -> None:
        media = self._media
        if media is None:
            return
        state = self._now_playing()
        if state == self._media_state:
            return
        self._media_state = state
        try:
            media.update(state)
        except Exception as exc:
            self._media_failed(exc)
            return
        interval = media.pump_interval
        if state is not None and interval is not None and self._media_timer is None:
            self._media_timer = self._app.set_interval(interval, self._pump_media)
        elif state is None:
            self._stop_media_timer()

    def _now_playing(self) -> NowPlaying | None:
        if self._runner is None:
            return None
        return NowPlaying(
            title=self._current_title or ALBUM_TITLE,
            artist=self._current_provider,
            status=PlaybackStatus.PAUSED if self._paused else PlaybackStatus.PLAYING,
        )

    def _pump_media(self) -> None:
        media = self._media
        if media is None:
            return
        try:
            media.pump()
        except Exception as exc:
            self._media_failed(exc)

    def _media_failed(self, exc: Exception) -> None:
        _log_media_error("media_controls_failed", exc)
        self._close_media()
        self._media = NullMediaControls()

    def _close_media(self) -> None:
        self._stop_media_timer()
        media = self._media
        self._media = None
        self._media_state = None
        if media is None:
            return
        try:
            media.close()
        except Exception as exc:
            _log_media_error("media_controls_close_failed", exc)

    def _stop_media_timer(self) -> None:
        timer = self._media_timer
        self._media_timer = None
        if timer is not None:
            timer.stop()

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
        position = _position(scope_articles, item.article_id)
        if position is None:
            return None
        article = scope_articles[position]
        mode = self._view_mode(item.scope_id)
        if mark_read and item.mark_read:
            self._mark_read(item, scope_articles, position)
        provider_name = provider_display_names(self._app.storage).get(article.provider_id, article.provider_id)
        segments = article_segments(
            self._app.ui,
            self._app.config,
            article,
            mode=mode,
            position=position,
            total=len(scope_articles),
            provider_name=provider_name,
            max_chars=self._engine_instance().max_chars,
        )
        if mark_read:
            self._current_title = article.translated_title or article.title
            self._current_provider = provider_name
        preparer = self._preparer
        return PlannedItem(
            article_id=article.article_id,
            scope_id=item.scope_id,
            mode=mode,
            segments=segments,
            prepared=preparer.pending_event(article.article_id) if preparer is not None else None,
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
        if self._preparer is not None:
            self._preparer.sync([item.article_id for item in self._items])

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
        self._sync_media()

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


def _position(articles: list[ArticleRecord], article_id: str) -> int | None:
    return next((index for index, article in enumerate(articles) if article.article_id == article_id), None)


def _log_media_error(event: str, exc: Exception) -> None:
    configure_tts_logger()
    LOGGER.warning("%s error_type=%s error=%s", event, type(exc).__name__, exc)
