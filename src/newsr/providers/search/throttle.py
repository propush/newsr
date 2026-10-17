from __future__ import annotations

import random
from threading import Lock
from time import monotonic, sleep
from typing import Callable

from ...cancellation import RefreshCancellation
from .errors import SearchCooldownError


class SearchThrottle:
    """Spaces search requests out and pauses background searches after challenges."""

    def __init__(
        self,
        *,
        min_interval: float = 2.0,
        jitter: float = 1.0,
        cooldown_initial: float = 120.0,
        cooldown_max: float = 3600.0,
        clock: Callable[[], float] = monotonic,
        uniform: Callable[[float, float], float] = random.uniform,
        wait: Callable[[float, RefreshCancellation | None], None] | None = None,
    ) -> None:
        if min_interval < 0 or jitter < 0:
            raise ValueError("min_interval and jitter must be non-negative")
        if cooldown_initial <= 0 or cooldown_max < cooldown_initial:
            raise ValueError("cooldown_initial must be positive and not exceed cooldown_max")
        self._min_interval = min_interval
        self._jitter = jitter
        self._cooldown_initial = cooldown_initial
        self._cooldown_max = cooldown_max
        self._clock = clock
        self._uniform = uniform
        self._wait = wait or _wait
        self._lock = Lock()
        self._next_slot_at: float | None = None
        self._cooldown_seconds = 0.0
        self._cooldown_until = 0.0

    def wait_turn(
        self,
        cancellation: RefreshCancellation | None = None,
        *,
        background: bool = False,
    ) -> None:
        with self._lock:
            now = self._clock()
            remaining = self._cooldown_until - now
            if background and remaining > 0:
                raise SearchCooldownError(remaining)
            slot_at = now if self._next_slot_at is None else max(now, self._next_slot_at)
            jitter = self._uniform(0.0, self._jitter) if self._jitter > 0 else 0.0
            self._next_slot_at = slot_at + self._min_interval + jitter
            delay = slot_at - now
        if delay > 0:
            self._wait(delay, cancellation)
        if cancellation is not None:
            cancellation.raise_if_cancelled()

    def record_challenge(self) -> float:
        with self._lock:
            if self._cooldown_seconds <= 0:
                self._cooldown_seconds = self._cooldown_initial
            else:
                self._cooldown_seconds = min(self._cooldown_seconds * 2, self._cooldown_max)
            self._cooldown_until = self._clock() + self._cooldown_seconds
            return self._cooldown_seconds

    def record_success(self) -> None:
        with self._lock:
            self._cooldown_seconds = 0.0
            self._cooldown_until = 0.0

    def cooldown_remaining(self) -> float:
        with self._lock:
            return max(0.0, self._cooldown_until - self._clock())


def _wait(delay: float, cancellation: RefreshCancellation | None) -> None:
    if cancellation is None:
        sleep(delay)
        return
    cancellation.cancelled_event.wait(delay)
