from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


class FakeRemoteCommand:
    def __init__(self, name: str) -> None:
        self.name = name
        self.enabled = False
        self.handlers: dict[int, Any] = {}
        self.preferred_intervals: list[float] = []
        self._next_token = 0

    def setEnabled_(self, enabled: bool) -> None:  # noqa: N802
        self.enabled = enabled

    def setPreferredIntervals_(self, intervals: list[float]) -> None:  # noqa: N802
        self.preferred_intervals = intervals

    def addTargetWithHandler_(self, handler: Any) -> int:  # noqa: N802
        self._next_token += 1
        self.handlers[self._next_token] = handler
        return self._next_token

    def removeTarget_(self, token: int) -> None:  # noqa: N802
        del self.handlers[token]

    def fire(self, event: Any = None) -> list[int]:
        return [handler(event) for handler in list(self.handlers.values())]


class FakeCommandCenter:
    names = (
        "togglePlayPauseCommand",
        "playCommand",
        "pauseCommand",
        "stopCommand",
        "nextTrackCommand",
        "previousTrackCommand",
        "skipForwardCommand",
        "skipBackwardCommand",
        "seekForwardCommand",
        "seekBackwardCommand",
    )

    def __init__(self) -> None:
        self.commands = {name: FakeRemoteCommand(name) for name in self.names}

    def __getattr__(self, name: str) -> Any:
        commands = self.__dict__["commands"]
        if name in commands:
            return lambda: commands[name]
        raise AttributeError(name)


class FakeInfoCenter:
    def __init__(self) -> None:
        self.info: dict[str, Any] | None = None
        self.state: int | None = None

    def setNowPlayingInfo_(self, info: dict[str, Any] | None) -> None:  # noqa: N802
        self.info = info

    def setPlaybackState_(self, state: int) -> None:  # noqa: N802
        self.state = state


class NativeDictionary(dict):
    def setObject_forKey_(self, value: Any, key: str) -> None:  # noqa: N802
        self[key] = value


class NativeValue:
    """Stands for a Foundation object built from a Python value."""

    def __init__(self, value: Any) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NativeValue) and other.value == self.value

    def __repr__(self) -> str:
        return f"NativeValue({self.value!r})"


class FakeSeekEvent:
    def __init__(self, event_type: int) -> None:
        self._type = event_type

    def type(self) -> int:
        return self._type


def install_fake_macos_modules(
    monkeypatch: pytest.MonkeyPatch,
    run_loop_results: list[int] | None = None,
    *,
    parent_application: str | None = None,
) -> SimpleNamespace:
    command_center = FakeCommandCenter()
    info_center = FakeInfoCenter()
    media_player = ModuleType("MediaPlayer")
    media_player.MPRemoteCommandCenter = SimpleNamespace(sharedCommandCenter=lambda: command_center)
    media_player.MPNowPlayingInfoCenter = SimpleNamespace(defaultCenter=lambda: info_center)
    media_player.MPMediaItemPropertyTitle = "title"
    media_player.MPMediaItemPropertyArtist = "artist"
    media_player.MPMediaItemPropertyAlbumTitle = "albumTitle"
    media_player.MPNowPlayingInfoPropertyPlaybackRate = "playbackRate"
    media_player.MPNowPlayingPlaybackStatePlaying = 1
    media_player.MPNowPlayingPlaybackStatePaused = 2
    media_player.MPNowPlayingPlaybackStateStopped = 3
    media_player.MPRemoteCommandHandlerStatusSuccess = 0
    media_player.MPSeekCommandEventTypeBeginSeeking = 0
    media_player.MPSeekCommandEventTypeEndSeeking = 1

    results = list(run_loop_results or [])
    run_loop_calls: list[tuple[str, float, bool]] = []

    def run_in_mode(mode: str, seconds: float, return_after_source: bool) -> int:
        run_loop_calls.append((mode, seconds, return_after_source))
        return results.pop(0) if results else 1

    core_foundation = ModuleType("CoreFoundation")
    core_foundation.CFRunLoopRunInMode = run_in_mode
    core_foundation.kCFRunLoopDefaultMode = "kCFRunLoopDefaultMode"
    core_foundation.kCFRunLoopRunHandledSource = 4

    foundation = ModuleType("Foundation")
    foundation.NSMutableDictionary = SimpleNamespace(dictionary=NativeDictionary)
    foundation.NSString = SimpleNamespace(stringWithString_=NativeValue)
    foundation.NSNumber = SimpleNamespace(numberWithDouble_=NativeValue)

    monkeypatch.setitem(sys.modules, "MediaPlayer", media_player)
    monkeypatch.setitem(sys.modules, "CoreFoundation", core_foundation)
    monkeypatch.setitem(sys.modules, "Foundation", foundation)

    from newsr.tts.media_controls import macos

    parents: list[str] = []
    monkeypatch.setattr(macos, "set_parent_application", parents.append)
    if parent_application is None:
        monkeypatch.delenv(macos.PARENT_APPLICATION_ENV, raising=False)
    else:
        monkeypatch.setenv(macos.PARENT_APPLICATION_ENV, parent_application)
    return SimpleNamespace(
        commands=command_center.commands,
        info=info_center,
        run_loop_calls=run_loop_calls,
        parents=parents,
    )
