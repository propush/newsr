from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

ALBUM_TITLE = "NewsR"


class MediaCommand(Enum):
    PLAY = "play"
    PAUSE = "pause"
    TOGGLE = "toggle"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    SEEK_FORWARD = "seek_forward"
    SEEK_BACKWARD = "seek_backward"


class PlaybackStatus(Enum):
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(frozen=True, slots=True)
class NowPlaying:
    title: str
    artist: str
    status: PlaybackStatus


CommandHandler = Callable[[MediaCommand], None]


class MediaControls(Protocol):
    """Operating-system media session: Now Playing metadata in and media-key commands out."""

    @property
    def pump_interval(self) -> float | None:
        """Seconds between `pump()` calls on the UI thread while a session is active, or None."""

    def start(self, handler: CommandHandler) -> None:
        """Set the command handler; it may be called from any thread."""

    def update(self, now_playing: NowPlaying | None) -> None:
        """Publish the current item, or release the session with None so other players get the keys."""

    def pump(self) -> None:
        ...

    def close(self) -> None:
        ...


class NullMediaControls:
    pump_interval: float | None = None

    def start(self, handler: CommandHandler) -> None:
        return

    def update(self, now_playing: NowPlaying | None) -> None:
        return

    def pump(self) -> None:
        return

    def close(self) -> None:
        return
