from __future__ import annotations

from collections.abc import Callable, Sequence
from threading import Condition, Event, Thread
from time import monotonic

from ..cancellation import RefreshCancellation
from ..providers.tts.base import LOGGER, PreparingTTSEngine, configure_tts_logger

SpeechTexts = tuple[tuple[str, str | None], ...]


class SpeechPreparer:
    """Prepares the speech of queued articles on one background thread, in playlist order.

    Each article has one event from its first submission until no job for it is pending or running,
    so playback can wait for an article even when its job is replaced. A running job is cancelled when
    its article leaves the playlist, so it does not hold up the articles behind it.
    """

    def __init__(self, engine: PreparingTTSEngine, on_change: Callable[[], None] | None = None) -> None:
        self._engine = engine
        self._on_change = on_change
        self._condition = Condition()
        self._pending: dict[str, SpeechTexts] = {}
        self._events: dict[str, Event] = {}
        self._running: tuple[str, RefreshCancellation] | None = None
        self._stopped = False
        self._thread: Thread | None = None

    @property
    def pending_count(self) -> int:
        with self._condition:
            return len(self._events)

    def pending_event(self, article_id: str) -> Event | None:
        with self._condition:
            return self._events.get(article_id)

    def submit(self, article_id: str, texts: Sequence[tuple[str, str | None]]) -> None:
        with self._condition:
            if self._stopped:
                return
            self._events.setdefault(article_id, Event())
            self._pending[article_id] = tuple(texts)
            if self._thread is None:
                self._thread = Thread(target=self._run, name="newsr-tts-prepare", daemon=True)
                self._thread.start()
            self._condition.notify_all()

    def sync(self, order: Sequence[str]) -> None:
        """Follow the playlist: prepare in its order and forget articles that left it."""
        position = {article_id: index for index, article_id in enumerate(order)}
        with self._condition:
            for article_id in [article_id for article_id in self._events if article_id not in position]:
                self._pending.pop(article_id, None)
                self._events.pop(article_id).set()
            if self._running is not None and self._running[0] not in position:
                self._running[1].cancel()
            self._pending = dict(sorted(self._pending.items(), key=lambda item: position[item[0]]))

    def stop(self) -> None:
        with self._condition:
            self._stopped = True
            if self._running is not None:
                self._running[1].cancel()
            self._pending.clear()
            for event in self._events.values():
                event.set()
            self._events.clear()
            self._condition.notify_all()

    def _run(self) -> None:
        configure_tts_logger()
        while True:
            with self._condition:
                while not self._pending and not self._stopped:
                    self._condition.wait()
                if self._stopped:
                    return
                article_id = next(iter(self._pending))
                texts = self._pending.pop(article_id)
                cancellation = RefreshCancellation()
                self._running = (article_id, cancellation)
            started = monotonic()
            try:
                self._engine.prepare(texts, cancellation)
            except Exception as exc:
                if self._stopped:
                    return
                if cancellation.is_cancelled:
                    LOGGER.info("speech_prepare_dropped article_id=%s", article_id)
                else:
                    LOGGER.warning(
                        "speech_prepare_failed article_id=%s error_type=%s error=%s",
                        article_id,
                        type(exc).__name__,
                        exc,
                    )
            else:
                LOGGER.info(
                    "speech_prepare_done article_id=%s texts=%s elapsed_s=%.2f",
                    article_id,
                    len(texts),
                    monotonic() - started,
                )
            with self._condition:
                self._running = None
                if article_id not in self._pending:
                    event = self._events.pop(article_id, None)
                    if event is not None:
                        event.set()
            self._notify()

    def _notify(self) -> None:
        if self._on_change is None:
            return
        try:
            self._on_change()
        except Exception as exc:
            LOGGER.warning("speech_prepare_notify_failed error_type=%s error=%s", type(exc).__name__, exc)
