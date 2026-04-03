from __future__ import annotations

from contextlib import contextmanager
from threading import Event, Lock, Timer
from time import monotonic
from typing import Any, Callable, Iterator


class RefreshCancelled(Exception):
    """Raised when a refresh is cancelled."""


class RefreshTimedOut(RefreshCancelled):
    """Raised when a refresh operation times out."""


class RefreshCancellation:
    def __init__(self) -> None:
        self._cancelled = Event()
        self._lock = Lock()
        self._closers: set[Callable[[], None]] = set()
        self._children: set[RefreshCancellation] = set()
        self._parent: RefreshCancellation | None = None
        self._reason = "cancelled"
        self._deadline_at: float | None = None
        self._timer: Timer | None = None

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def cancelled_event(self) -> Event:
        return self._cancelled

    @property
    def timed_out(self) -> bool:
        return self.is_cancelled and self._reason == "timeout"

    @property
    def deadline_at(self) -> float | None:
        return self._deadline_at

    def cancel(self) -> None:
        self._cancel("cancelled")

    def cancel_due_to_timeout(self) -> None:
        self._cancel("timeout")

    def _cancel(self, reason: str) -> None:
        self._cancelled.set()
        with self._lock:
            closers = list(self._closers)
            children = list(self._children)
            timer = self._timer
            self._reason = reason
            self._timer = None
        if timer is not None:
            timer.cancel()
        for closer in closers:
            try:
                closer()
            except Exception:
                continue
        for child in children:
            if reason == "timeout":
                child.cancel_due_to_timeout()
            else:
                child.cancel()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            if self._reason == "timeout":
                raise RefreshTimedOut()
            raise RefreshCancelled()

    def remaining_timeout(self) -> float | None:
        deadline_at = self._deadline_at
        if deadline_at is None:
            return None
        return max(0.0, deadline_at - monotonic())

    def child_with_timeout(self, timeout_seconds: float) -> RefreshCancellation:
        child = RefreshCancellation()
        child._parent = self
        child._deadline_at = monotonic() + timeout_seconds
        with self._lock:
            self._children.add(child)
        child._timer = Timer(timeout_seconds, child.cancel_due_to_timeout)
        child._timer.daemon = True
        child._timer.start()
        if self.is_cancelled:
            if self.timed_out:
                child.cancel_due_to_timeout()
            else:
                child.cancel()
        return child

    def finish(self) -> None:
        with self._lock:
            timer = self._timer
            self._timer = None
            children = list(self._children)
            self._children.clear()
        if timer is not None:
            timer.cancel()
        for child in children:
            child.finish()
        parent = self._parent
        if parent is not None:
            with parent._lock:
                parent._children.discard(self)
            self._parent = None

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


def resolve_request_timeout(
    cancellation: RefreshCancellation | None,
    default_timeout: float,
) -> float:
    if cancellation is None:
        return default_timeout
    remaining = cancellation.remaining_timeout()
    if remaining is None:
        return default_timeout
    return max(0.001, min(default_timeout, remaining))
