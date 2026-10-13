from __future__ import annotations

import enum
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from newsr.tts.media_controls import MediaCommand, NowPlaying, PlaybackStatus
from newsr.tts.media_controls.windows import WindowsMediaControls


class Button(enum.IntEnum):
    PLAY = 0
    PAUSE = 1
    STOP = 2
    RECORD = 3
    FAST_FORWARD = 4
    REWIND = 5
    NEXT = 6
    PREVIOUS = 7


class Status(enum.IntEnum):
    STOPPED = 2
    PLAYING = 3
    PAUSED = 4


class FakeDisplayUpdater:
    def __init__(self) -> None:
        self.type: int | None = None
        self.music_properties = SimpleNamespace(title="", artist="", album_title="")
        self.updates = 0
        self.cleared = 0

    def update(self) -> None:
        self.updates += 1

    def clear_all(self) -> None:
        self.cleared += 1
        self.music_properties = SimpleNamespace(title="", artist="", album_title="")


class FakeTransportControls:
    def __init__(self) -> None:
        self.is_enabled = False
        self.playback_status: Status | None = None
        self.display_updater = FakeDisplayUpdater()
        self.handlers: dict[int, Any] = {}

    def add_button_pressed(self, handler: Any) -> int:
        self.handlers[1] = handler
        return 1

    def remove_button_pressed(self, token: int) -> None:
        del self.handlers[token]

    def press(self, button: int) -> None:
        for handler in list(self.handlers.values()):
            handler(self, SimpleNamespace(button=button))


class FakeMediaPlayer:
    instances: list[FakeMediaPlayer] = []

    def __init__(self) -> None:
        self.command_manager = SimpleNamespace(is_enabled=True)
        self.system_media_transport_controls = FakeTransportControls()
        self.closed = False
        FakeMediaPlayer.instances.append(self)

    def close(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def winrt_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    media = ModuleType("winrt.windows.media")
    media.SystemMediaTransportControlsButton = Button
    media.MediaPlaybackStatus = Status
    media.MediaPlaybackType = SimpleNamespace(MUSIC=1)
    playback = ModuleType("winrt.windows.media.playback")
    playback.MediaPlayer = FakeMediaPlayer
    media.playback = playback
    windows = ModuleType("winrt.windows")
    windows.media = media
    winrt = ModuleType("winrt")
    winrt.windows = windows
    for name, module in (
        ("winrt", winrt),
        ("winrt.windows", windows),
        ("winrt.windows.media", media),
        ("winrt.windows.media.playback", playback),
    ):
        monkeypatch.setitem(sys.modules, name, module)
    FakeMediaPlayer.instances = []


def test_windows_media_controls_publish_metadata_and_forward_buttons() -> None:
    received: list[MediaCommand] = []
    controls = WindowsMediaControls()
    controls.start(received.append)
    transport = FakeMediaPlayer.instances[-1].system_media_transport_controls

    assert FakeMediaPlayer.instances[-1].command_manager.is_enabled is False
    controls.update(NowPlaying(title="Title 1", artist="BBC News", status=PlaybackStatus.PLAYING))

    assert transport.is_enabled is True
    assert transport.is_next_enabled is True and transport.is_rewind_enabled is True
    assert transport.playback_status is Status.PLAYING
    updater = transport.display_updater
    assert (updater.music_properties.title, updater.music_properties.artist) == ("Title 1", "BBC News")
    assert updater.music_properties.album_title == "NewsR"
    assert updater.updates == 1

    for button in (Button.PLAY, Button.PAUSE, Button.STOP, Button.NEXT, Button.PREVIOUS, Button.RECORD):
        transport.press(button)
    transport.press(Button.FAST_FORWARD)
    transport.press(Button.REWIND)

    assert received == [
        MediaCommand.PLAY,
        MediaCommand.PAUSE,
        MediaCommand.STOP,
        MediaCommand.NEXT,
        MediaCommand.PREVIOUS,
        MediaCommand.SEEK_FORWARD,
        MediaCommand.SEEK_BACKWARD,
    ]


def test_windows_media_controls_pause_release_and_close() -> None:
    controls = WindowsMediaControls()
    controls.start(lambda _command: None)
    instance = FakeMediaPlayer.instances[-1]
    transport = instance.system_media_transport_controls

    controls.update(NowPlaying(title="Title 1", artist="BBC News", status=PlaybackStatus.PAUSED))
    assert transport.playback_status is Status.PAUSED

    controls.update(None)
    assert transport.is_enabled is False
    assert transport.playback_status is Status.STOPPED
    assert transport.handlers == {}
    assert transport.display_updater.cleared == 1

    controls.close()
    assert instance.closed is True
