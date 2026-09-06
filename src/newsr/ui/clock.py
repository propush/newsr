from __future__ import annotations

import asyncio
from datetime import datetime

from rich.text import Text
from textual.app import ComposeResult, RenderResult
from textual.events import Mount
from textual.reactive import Reactive
from textual.widgets import Header
from textual.widgets._header import HeaderClock, HeaderClockSpace


def minute_time_format() -> str:
    """Return a minute-only format matching the system's 12/24-hour convention."""
    sample = datetime(2000, 1, 1, 13, 5)
    meridiem = sample.strftime("%p")
    if meridiem and meridiem in sample.strftime("%X"):
        return "%I:%M %p"
    return "%H:%M"


def seconds_until_next_minute(now: datetime) -> float:
    """Return the wall-clock delay until the next minute boundary."""
    return 60.0 - now.second - now.microsecond / 1_000_000


def _minute_key(now: datetime) -> tuple[int, int, int, int, int]:
    return now.year, now.month, now.day, now.hour, now.minute


def _now() -> datetime:
    return datetime.now()


class MinuteHeaderClock(HeaderClockSpace):
    """A header clock that refreshes only after the displayed minute changes."""

    DEFAULT_CSS = """
    MinuteHeaderClock {
        background: $foreground-darken-1 5%;
        color: $foreground;
        text-opacity: 85%;
        content-align: center middle;
    }
    """

    time_format: Reactive[str] = Reactive("%H:%M")

    def _on_mount(self, _: Mount) -> None:
        self._last_minute = _minute_key(_now())
        self.run_worker(
            self._refresh_on_minute_change,
            name="update header clock each minute",
            group="header-clock",
            exclusive=True,
        )

    async def _refresh_on_minute_change(self) -> None:
        while True:
            now = _now()
            await asyncio.sleep(seconds_until_next_minute(now))
            self._refresh_if_minute_changed(_now())

    def _refresh_if_minute_changed(self, now: datetime) -> bool:
        minute = _minute_key(now)
        if minute == self._last_minute:
            return False
        self._last_minute = minute
        self.refresh()
        return True

    def render(self) -> RenderResult:
        return Text(_now().time().strftime(self.time_format))


class ConfiguredHeader(Header):
    """The NewsR header with a configurable clock refresh cadence."""

    def __init__(self, clock: str) -> None:
        self._clock = clock
        super().__init__(
            show_clock=clock != "none",
            time_format=minute_time_format() if clock == "no_seconds" else None,
        )

    def compose(self) -> ComposeResult:
        for child in super().compose():
            if self._clock == "no_seconds" and isinstance(child, HeaderClock):
                yield MinuteHeaderClock().data_bind(Header.time_format)
            else:
                yield child
