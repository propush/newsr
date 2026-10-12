from __future__ import annotations

from threading import Event, Lock, Semaphore

from newsr.cancellation import RefreshCancellation
from newsr.providers.tts.base import SynthesizedAudio, TTSEngineError


class FakeTTSEngine:
    name = "fake"

    def __init__(self, *, max_chars: int = 1000, fail_on: str | None = None) -> None:
        self.max_chars = max_chars
        self.fail_on = fail_on
        self.calls: list[tuple[str, str | None]] = []
        self._lock = Lock()

    def synthesize(
        self,
        text: str,
        language: str | None,
        cancellation: RefreshCancellation | None = None,
    ) -> SynthesizedAudio:
        with self._lock:
            self.calls.append((text, language))
        if self.fail_on is not None and self.fail_on in text:
            raise TTSEngineError(f"cannot speak {self.fail_on}")
        return SynthesizedAudio(data=text.encode("utf-8"), format="wav")


class FakeAudioOutput:
    """Plays clips instantly, or blocks each clip until `release()` when `auto_finish` is False."""

    def __init__(self, *, auto_finish: bool = True) -> None:
        self.auto_finish = auto_finish
        self.played: list[str] = []
        self.paused = False
        self.closed = False
        self._released = Semaphore(0)
        self._stopped = Event()
        self._lock = Lock()

    @property
    def is_paused(self) -> bool:
        return self.paused

    def play(self, audio: SynthesizedAudio, cancellation: RefreshCancellation | None = None) -> bool:
        with self._lock:
            self.played.append(audio.data.decode("utf-8"))
        self._stopped.clear()
        if self.auto_finish:
            return True
        while True:
            if cancellation is not None and cancellation.is_cancelled:
                cancellation.raise_if_cancelled()
            if self._stopped.is_set():
                self._stopped.clear()
                return False
            if self._released.acquire(timeout=0.01):
                return True

    def release(self, count: int = 1) -> None:
        for _ in range(count):
            self._released.release()

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def stop_clip(self) -> None:
        self._stopped.set()

    def close(self) -> None:
        self.closed = True
