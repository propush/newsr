from __future__ import annotations

from collections.abc import Generator
from threading import Event, Lock
from typing import Any, Protocol

from ..cancellation import RefreshCancellation
from ..providers.tts.base import SynthesizedAudio

SAMPLE_RATE = 44100
CHANNELS = 2
SAMPLE_WIDTH = 2
_FRAME_BYTES = CHANNELS * SAMPLE_WIDTH
_WAIT_SECONDS = 0.05
SILENCE_THRESHOLD = 256
LEADING_SILENCE_SECONDS = 0.08
TRAILING_SILENCE_SECONDS = 0.3
_SILENCE_SCAN_SECONDS = 3.0


def trim_silence(pcm: bytes) -> bytes:
    """Shorten the silence some engines add around speech in 16-bit stereo PCM."""
    samples = memoryview(pcm).cast("h")
    frames = len(samples) // CHANNELS
    scan = min(frames, int(_SILENCE_SCAN_SECONDS * SAMPLE_RATE))

    def audible(frame: int) -> bool:
        offset = frame * CHANNELS
        return any(abs(samples[offset + channel]) > SILENCE_THRESHOLD for channel in range(CHANNELS))

    first = next((frame for frame in range(scan) if audible(frame)), None)
    last = next((frame for frame in range(frames - 1, frames - 1 - scan, -1) if audible(frame)), None)
    start = 0 if first is None else max(0, first - int(LEADING_SILENCE_SECONDS * SAMPLE_RATE))
    end = frames if last is None else min(frames, last + 1 + int(TRAILING_SILENCE_SECONDS * SAMPLE_RATE))
    if end <= start:
        return pcm
    return pcm[start * _FRAME_BYTES : end * _FRAME_BYTES]


class AudioOutputError(RuntimeError):
    """Raised when audio cannot be decoded or played."""


class AudioOutput(Protocol):
    @property
    def is_paused(self) -> bool:
        ...

    def play(self, audio: SynthesizedAudio, cancellation: RefreshCancellation | None = None) -> bool:
        """Play a clip and block until it ends (True) or is stopped (False)."""

    def pause(self) -> None:
        ...

    def resume(self) -> None:
        ...

    def stop_clip(self) -> None:
        ...

    def close(self) -> None:
        ...


class MiniaudioOutput:
    def __init__(self) -> None:
        self._lock = Lock()
        self._device: Any = None
        self._pcm: memoryview | None = None
        self._position = 0
        self._paused = False
        self._clip_done = Event()
        self._completed = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def play(self, audio: SynthesizedAudio, cancellation: RefreshCancellation | None = None) -> bool:
        pcm = self._decode(audio)
        with self._lock:
            self._pcm = memoryview(pcm)
            self._position = 0
            self._completed = False
            self._clip_done.clear()
        self._ensure_device()
        while not self._clip_done.wait(_WAIT_SECONDS):
            if cancellation is not None and cancellation.is_cancelled:
                self.stop_clip()
                cancellation.raise_if_cancelled()
        return self._completed

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop_clip(self) -> None:
        with self._lock:
            self._pcm = None
            self._completed = False
        self._clip_done.set()

    def close(self) -> None:
        self.stop_clip()
        with self._lock:
            device = self._device
            self._device = None
        if device is not None:
            device.close()

    @staticmethod
    def _decode(audio: SynthesizedAudio) -> bytes:
        import miniaudio

        try:
            decoded = miniaudio.decode(
                audio.data,
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=CHANNELS,
                sample_rate=SAMPLE_RATE,
            )
        except miniaudio.MiniaudioError as exc:
            raise AudioOutputError(f"could not decode {audio.format} audio: {exc}") from exc
        return trim_silence(decoded.samples.tobytes())

    def _ensure_device(self) -> None:
        with self._lock:
            if self._device is not None:
                return
        import miniaudio

        try:
            device = miniaudio.PlaybackDevice(
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=CHANNELS,
                sample_rate=SAMPLE_RATE,
                app_name="newsr",
            )
            stream = self._stream()
            next(stream)
            device.start(stream)
        except miniaudio.MiniaudioError as exc:
            raise AudioOutputError(f"could not open the audio device: {exc}") from exc
        with self._lock:
            self._device = device

    def _stream(self) -> Generator[bytes, int, None]:
        frames = yield b""
        while True:
            size = frames * _FRAME_BYTES
            with self._lock:
                pcm = self._pcm
                if pcm is None or self._paused:
                    chunk = b""
                else:
                    chunk = bytes(pcm[self._position : self._position + size])
                    self._position += len(chunk)
                    if self._position >= len(pcm):
                        self._pcm = None
                        self._completed = True
                        self._clip_done.set()
            frames = yield chunk + bytes(size - len(chunk))
