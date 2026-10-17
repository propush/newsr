from __future__ import annotations

import pytest

from newsr.cancellation import RefreshCancellation, RefreshCancelled
from newsr.providers.search import SearchCooldownError, SearchThrottle


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def build_throttle(clock: FakeClock, waits: list[float], **kwargs) -> SearchThrottle:
    def wait(delay: float, cancellation: RefreshCancellation | None) -> None:
        waits.append(delay)
        clock.now += delay

    options = {"min_interval": 2.0, "jitter": 0.0, "clock": clock, "wait": wait}
    options.update(kwargs)
    return SearchThrottle(**options)


def test_first_request_runs_immediately_and_following_requests_are_spaced() -> None:
    clock = FakeClock()
    waits: list[float] = []
    throttle = build_throttle(clock, waits)

    throttle.wait_turn()
    throttle.wait_turn()
    clock.now += 0.5
    throttle.wait_turn()

    assert waits == [2.0, 1.5]


def test_requests_after_a_long_pause_do_not_wait() -> None:
    clock = FakeClock()
    waits: list[float] = []
    throttle = build_throttle(clock, waits)

    throttle.wait_turn()
    clock.now += 10
    throttle.wait_turn()

    assert waits == []


def test_jitter_is_added_to_the_interval_within_bounds() -> None:
    clock = FakeClock()
    waits: list[float] = []
    bounds: list[tuple[float, float]] = []

    def uniform(low: float, high: float) -> float:
        bounds.append((low, high))
        return high

    throttle = build_throttle(clock, waits, jitter=1.0, uniform=uniform)

    throttle.wait_turn()
    throttle.wait_turn()

    assert bounds[0] == (0.0, 1.0)
    assert waits == [3.0]


def test_cooldown_doubles_up_to_the_cap_and_success_resets_it() -> None:
    clock = FakeClock()
    throttle = build_throttle(clock, [], cooldown_initial=120.0, cooldown_max=400.0)

    assert throttle.record_challenge() == 120.0
    assert throttle.record_challenge() == 240.0
    assert throttle.record_challenge() == 400.0
    assert throttle.cooldown_remaining() == 400.0

    throttle.record_success()

    assert throttle.cooldown_remaining() == 0.0
    assert throttle.record_challenge() == 120.0


def test_background_callers_are_refused_during_cooldown_and_interactive_callers_proceed() -> None:
    clock = FakeClock()
    waits: list[float] = []
    throttle = build_throttle(clock, waits, min_interval=0.0)
    throttle.record_challenge()
    clock.now += 30

    with pytest.raises(SearchCooldownError) as exc_info:
        throttle.wait_turn(background=True)
    throttle.wait_turn()

    assert exc_info.value.remaining_seconds == 90.0
    assert "retry in 90 s" in str(exc_info.value)
    clock.now += 90
    throttle.wait_turn(background=True)


def test_cancellation_during_wait_raises_refresh_cancelled() -> None:
    clock = FakeClock()
    cancellation = RefreshCancellation()

    def wait(delay: float, active_cancellation: RefreshCancellation | None) -> None:
        assert active_cancellation is cancellation
        cancellation.cancel()

    throttle = SearchThrottle(min_interval=2.0, jitter=0.0, clock=clock, wait=wait)
    throttle.wait_turn(cancellation)

    with pytest.raises(RefreshCancelled):
        throttle.wait_turn(cancellation)


def test_default_wait_returns_early_when_cancelled() -> None:
    cancellation = RefreshCancellation()
    cancellation.cancel()
    throttle = SearchThrottle(min_interval=60.0, jitter=0.0)
    throttle.wait_turn()

    with pytest.raises(RefreshCancelled):
        throttle.wait_turn(cancellation)


def test_throttle_rejects_invalid_settings() -> None:
    with pytest.raises(ValueError):
        SearchThrottle(min_interval=-1)
    with pytest.raises(ValueError):
        SearchThrottle(cooldown_initial=10, cooldown_max=5)
