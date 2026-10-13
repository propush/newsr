from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Any, Protocol

from ..cancellation import RefreshCancellation, RefreshCancelled
from ..domain.reader import ViewMode
from ..providers.tts.base import LOGGER, SynthesizedAudio, TTSEngine
from .player import AudioOutput
from .script import SpeechSegment

_POLL_SECONDS = 0.1
_PREFETCH_SEGMENTS = 3
SEGMENT_RESTART_SECONDS = 3.0


@dataclass(frozen=True, slots=True)
class PlannedItem:
    article_id: str
    scope_id: str
    mode: ViewMode
    segments: tuple[SpeechSegment, ...]


class PlaybackHost(Protocol):
    def start_next_item(self, runner: PlaybackRunner) -> PlannedItem | None:
        """Mark the queue head as started and return its script (runs on the UI thread)."""

    def peek_next_item(self, runner: PlaybackRunner, after_article_id: str) -> PlannedItem | None:
        """Return the script of the item queued after the given one (runs on the UI thread)."""

    def item_finished(self, runner: PlaybackRunner, article_id: str) -> None:
        ...

    def buffering_changed(self, runner: PlaybackRunner, buffering: bool) -> None:
        ...

    def playback_failed(self, runner: PlaybackRunner, article_id: str | None, message: str) -> None:
        ...

    def playback_finished(self, runner: PlaybackRunner) -> None:
        ...


Dispatch = Callable[..., Any]
SegmentKey = tuple[str, str | None]


class PlaybackRunner:
    def __init__(
        self,
        *,
        host: PlaybackHost,
        engine_provider: Callable[[], TTSEngine],
        output: AudioOutput,
        dispatch: Dispatch,
    ) -> None:
        self._host = host
        self._engine_provider = engine_provider
        self._output = output
        self._dispatch = dispatch
        self._cancellation = RefreshCancellation()
        self._skip = Event()
        self._restart = Event()
        self._seek = Event()
        self._seek_lock = Lock()
        self._seek_target: int | None = None
        self._segment_index: int | None = None
        self._futures: dict[SegmentKey, Future[SynthesizedAudio]] = {}
        self._thread: Thread | None = None

    @property
    def is_cancelled(self) -> bool:
        return self._cancellation.is_cancelled

    @property
    def current_segment_index(self) -> int | None:
        return self._segment_index

    def start(self) -> None:
        self._thread = Thread(target=self._run, name="newsr-tts-playback", daemon=True)
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def skip(self) -> None:
        self._skip.set()
        self._output.stop_clip()

    def restart_item(self) -> None:
        self._restart.set()
        self._output.stop_clip()

    def seek_segment(self, delta: int) -> None:
        """Move by `delta` segments; moving back first restarts a segment that has played for a while."""
        with self._seek_lock:
            pending = self._seek_target
            index = self._segment_index if pending is None else pending
            if index is None or delta == 0:
                return
            if delta < 0 and pending is None and self._output.elapsed_seconds > SEGMENT_RESTART_SECONDS:
                delta += 1
            self._seek_target = max(0, index + delta)
            self._seek.set()
        self._output.stop_clip()

    def stop(self) -> None:
        self._cancellation.cancel()
        self._output.stop_clip()

    def _run(self) -> None:
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="newsr-tts-synth")
        try:
            engine = self._engine_provider()
            while not self._cancellation.is_cancelled:
                item = self._dispatch(self._host.start_next_item, self)
                if item is None:
                    self._dispatch(self._host.playback_finished, self)
                    return
                outcome = self._play_item(item, engine, executor)
                if outcome == "restart":
                    continue
                if outcome == "failed":
                    return
                self._dispatch(self._host.item_finished, self, item.article_id)
        except RefreshCancelled:
            return
        except Exception as exc:
            LOGGER.error("playback_failed error_type=%s error=%s", type(exc).__name__, exc)
            if not self._cancellation.is_cancelled:
                self._safe_dispatch(self._host.playback_failed, self, None, str(exc))
        finally:
            self._cancellation.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

    def _play_item(self, item: PlannedItem, engine: TTSEngine, executor: ThreadPoolExecutor) -> str:
        self._skip.clear()
        self._restart.clear()
        self._take_seek()
        self._retain({(segment.text, segment.language) for segment in item.segments})
        index = 0
        try:
            while index < len(item.segments):
                self._segment_index = index
                future = self._future_for(item.segments[index], engine, executor)
                self._prefetch(item, index, engine, executor)
                try:
                    audio = self._await(future)
                except RefreshCancelled:
                    raise
                except Exception as exc:
                    if not self._interrupted():
                        self._safe_dispatch(self._host.playback_failed, self, item.article_id, str(exc))
                        return "failed"
                    audio = None
                if audio is not None and not self._interrupted():
                    completed = self._output.play(audio, self._cancellation)
                    self._cancellation.raise_if_cancelled()
                    if completed and not self._interrupted():
                        index += 1
                        continue
                target = None if self._skip.is_set() or self._restart.is_set() else self._take_seek()
                if target is None:
                    return self._interruption()
                index = target
        finally:
            self._segment_index = None
        return "completed"

    def _prefetch(self, item: PlannedItem, index: int, engine: TTSEngine, executor: ThreadPoolExecutor) -> None:
        ahead = list(item.segments[index + 1 : index + 1 + _PREFETCH_SEGMENTS])
        missing = _PREFETCH_SEGMENTS - len(ahead)
        if missing > 0:
            upcoming = self._dispatch(self._host.peek_next_item, self, item.article_id)
            if upcoming is not None:
                ahead.extend(upcoming.segments[:missing])
        for segment in ahead:
            self._future_for(segment, engine, executor)

    def _future_for(
        self,
        segment: SpeechSegment,
        engine: TTSEngine,
        executor: ThreadPoolExecutor,
    ) -> Future[SynthesizedAudio]:
        key = (segment.text, segment.language)
        future = self._futures.get(key)
        if future is None:
            future = executor.submit(engine.synthesize, segment.text, segment.language, self._cancellation)
            self._futures[key] = future
        return future

    def _await(self, future: Future[SynthesizedAudio]) -> SynthesizedAudio | None:
        if future.done():
            return future.result()
        self._dispatch(self._host.buffering_changed, self, True)
        try:
            while True:
                self._cancellation.raise_if_cancelled()
                if self._interrupted():
                    return None
                try:
                    return future.result(timeout=_POLL_SECONDS)
                except FutureTimeoutError:
                    continue
        finally:
            self._safe_dispatch(self._host.buffering_changed, self, False)

    def _retain(self, keys: set[SegmentKey]) -> None:
        for key in list(self._futures):
            if key not in keys:
                self._futures.pop(key).cancel()

    def _take_seek(self) -> int | None:
        with self._seek_lock:
            target = self._seek_target
            self._seek_target = None
            self._seek.clear()
        return target

    def _interrupted(self) -> bool:
        return self._skip.is_set() or self._restart.is_set() or self._seek.is_set()

    def _interruption(self) -> str:
        self._cancellation.raise_if_cancelled()
        if self._restart.is_set():
            return "restart"
        return "skipped"

    def _safe_dispatch(self, callback: Callable[..., Any], *args: Any) -> None:
        try:
            self._dispatch(callback, *args)
        except Exception:
            return
