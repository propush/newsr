from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import Mock

import pytest
from textual.app import App, ComposeResult
from textual.widgets._header import HeaderClock

import newsr.ui.clock as clock_module
from newsr.ui.clock import (
    ConfiguredHeader,
    MinuteHeaderClock,
    minute_time_format,
    seconds_until_next_minute,
)


class ClockTestApp(App[None]):
    def __init__(self, mode: str) -> None:
        super().__init__()
        self.mode = mode

    def compose(self) -> ComposeResult:
        yield ConfiguredHeader(self.mode)


@pytest.mark.parametrize("mode", ["none", "seconds", "no_seconds"])
def test_configured_header_selects_clock_for_mode(mode: str) -> None:
    app = ClockTestApp(mode)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            clocks = list(app.query(HeaderClock))
            minute_clocks = list(app.query(MinuteHeaderClock))
            if mode == "none":
                assert clocks == []
                assert minute_clocks == []
            elif mode == "seconds":
                assert len(clocks) == 1
                assert type(clocks[0]) is HeaderClock
                assert minute_clocks == []
            else:
                assert clocks == []
                assert len(minute_clocks) == 1
                assert len(minute_clocks[0]._timers) == 0

    asyncio.run(runner())


def test_minute_clock_render_does_not_change_with_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = datetime(2026, 9, 6, 9, 5, 1)
    monkeypatch.setattr(clock_module, "_now", lambda: current)
    clock = MinuteHeaderClock()
    clock.time_format = "%H:%M"

    first = clock.render().plain
    current = current.replace(second=59, microsecond=999_999)
    second = clock.render().plain

    assert first == second == "09:05"


@pytest.mark.parametrize(
    ("localized_time", "meridiem", "expected"),
    [
        ("13:05:00", "PM", "%H:%M"),
        ("01:05:00 PM", "PM", "%I:%M %p"),
    ],
)
def test_minute_time_format_follows_system_hour_convention(
    monkeypatch: pytest.MonkeyPatch,
    localized_time: str,
    meridiem: str,
    expected: str,
) -> None:
    sample = Mock()
    sample.strftime.side_effect = lambda pattern: {
        "%X": localized_time,
        "%p": meridiem,
    }[pattern]
    datetime_factory = Mock(return_value=sample)
    monkeypatch.setattr(clock_module, "datetime", datetime_factory)

    assert minute_time_format() == expected


def test_minute_clock_refreshes_at_most_once_per_minute() -> None:
    clock = MinuteHeaderClock()
    clock._last_minute = (2026, 9, 6, 9, 5)
    refresh = Mock()
    clock.refresh = refresh  # type: ignore[method-assign]

    assert clock._refresh_if_minute_changed(datetime(2026, 9, 6, 9, 5, 30)) is False
    assert clock._refresh_if_minute_changed(datetime(2026, 9, 6, 9, 6, 0)) is True
    assert clock._refresh_if_minute_changed(datetime(2026, 9, 6, 9, 6, 59)) is False
    assert clock._refresh_if_minute_changed(datetime(2026, 9, 6, 9, 7, 0)) is True
    assert refresh.call_count == 2


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 9, 6, 9, 5, 0), 60.0),
        (datetime(2026, 9, 6, 9, 5, 30), 30.0),
        (datetime(2026, 9, 6, 9, 5, 59, 500_000), 0.5),
    ],
)
def test_seconds_until_next_minute_is_wall_clock_aligned(
    now: datetime,
    expected: float,
) -> None:
    assert seconds_until_next_minute(now) == expected
