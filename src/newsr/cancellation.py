from __future__ import annotations

from contextlib import contextmanager
from threading import Event, Lock
from typing import Any, Callable, Iterator


class RefreshCancelled(Exception):
    """Raised when a refresh is cancelled."""


class RefreshCancellation:
    def __init__(self) -> None:
        self._cancelled = Event()
        self._lock = Lock()
        self._closers: set[Callable[[], None]] = set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def cancelled_event(self) -> Event:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled.set()
        with self._lock:
            closers = list(self._closers)
        for closer in closers:
            try:
                closer()
            except Exception:
                continue

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise RefreshCancelled()

    @contextmanager
    def track_close(self, closer: Callable[[], None]) -> Iterator[None]:
        self.raise_if_cancelled()
        with self._lock:
            self._closers.add(closer)
        try:
            self.raise_if_cancelled()
            yield
        finally:
            with self._lock:
                self._closers.discard(closer)


def cancellable_read(
    response: Any, cancellation: RefreshCancellation | None
) -> bytes:
    if cancellation is None:
        return response.read()
    with cancellation.track_close(response.close):
        chunks: list[bytes] = []
        while True:
            cancellation.raise_if_cancelled()
            chunk = response.read(8192)
            if not chunk:
                break
            chunks.append(chunk)
        cancellation.raise_if_cancelled()
        return b"".join(chunks)
