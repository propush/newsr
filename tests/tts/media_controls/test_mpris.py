from __future__ import annotations

import asyncio
from typing import Any

import pytest

pytest.importorskip("dbus_fast")

from newsr.tts.media_controls import MediaCommand, NowPlaying, PlaybackStatus  # noqa: E402
from newsr.tts.media_controls.mpris import NO_TRACK, OBJECT_PATH, MprisMediaControls  # noqa: E402

PLAYING = NowPlaying(title="Title 1", artist="BBC News", status=PlaybackStatus.PLAYING)


class FakeBus:
    def __init__(self) -> None:
        self.exported: list[tuple[str, str]] = []
        self.calls: list[tuple[str, str]] = []
        self.disconnected = False

    def export(self, path: str, interface: Any) -> None:
        self.exported.append((path, interface.name))

    async def request_name(self, name: str) -> None:
        self.calls.append(("request", name))

    async def release_name(self, name: str) -> None:
        self.calls.append(("release", name))

    def disconnect(self) -> None:
        self.disconnected = True


def test_mpris_player_methods_forward_commands() -> None:
    received: list[MediaCommand] = []
    controls = MprisMediaControls()
    controls.start(received.append)
    player = controls.player

    player.PlayPause()
    player.Play()
    player.Pause()
    player.Stop()
    player.Next()
    player.Previous()
    player.Seek(5_000_000)
    player.Seek(-5_000_000)
    player.Seek(0)

    assert received == [
        MediaCommand.TOGGLE,
        MediaCommand.PLAY,
        MediaCommand.PAUSE,
        MediaCommand.STOP,
        MediaCommand.NEXT,
        MediaCommand.PREVIOUS,
        MediaCommand.SEEK_FORWARD,
        MediaCommand.SEEK_BACKWARD,
    ]


def test_mpris_player_reports_status_and_metadata_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    player = MprisMediaControls().player
    changes: list[dict[str, Any]] = []
    monkeypatch.setattr(player, "emit_properties_changed", changes.append)

    player.set_now_playing(PLAYING)
    player.set_now_playing(NowPlaying(title="Title 1", artist="BBC News", status=PlaybackStatus.PAUSED))
    player.set_now_playing(NowPlaying(title="Title 2", artist="BBC News", status=PlaybackStatus.PAUSED))
    player.set_now_playing(None)

    assert [sorted(change) for change in changes] == [
        ["Metadata", "PlaybackStatus"],
        ["PlaybackStatus"],
        ["Metadata"],
        ["Metadata", "PlaybackStatus"],
    ]
    assert changes[0]["PlaybackStatus"] == "Playing"
    assert changes[0]["Metadata"]["xesam:title"].value == "Title 1"
    assert changes[0]["Metadata"]["xesam:artist"].value == ["BBC News"]
    assert changes[2]["Metadata"]["mpris:trackid"].value != changes[0]["Metadata"]["mpris:trackid"].value
    assert changes[3]["PlaybackStatus"] == "Stopped"
    assert changes[3]["Metadata"]["mpris:trackid"].value == NO_TRACK
    assert player.PlaybackStatus == "Stopped"


def test_mpris_media_controls_own_the_bus_name_only_while_active() -> None:
    bus = FakeBus()

    async def connect() -> FakeBus:
        return bus

    async def scenario() -> None:
        controls = MprisMediaControls(bus_factory=connect)
        controls.update(PLAYING)
        controls.update(NowPlaying(title="Title 1", artist="BBC News", status=PlaybackStatus.PAUSED))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        controls.update(None)
        await asyncio.sleep(0)
        controls.update(PLAYING)
        await asyncio.sleep(0)
        controls.close()

    asyncio.run(scenario())

    assert bus.exported == [
        (OBJECT_PATH, "org.mpris.MediaPlayer2"),
        (OBJECT_PATH, "org.mpris.MediaPlayer2.Player"),
    ]
    assert [call for call, _name in bus.calls] == ["request", "release", "request"]
    assert bus.calls[0][1].startswith("org.mpris.MediaPlayer2.newsr.instance")
    assert bus.disconnected is True


def test_mpris_media_controls_go_inert_when_the_session_bus_is_unavailable() -> None:
    attempts: list[int] = []

    async def connect() -> FakeBus:
        attempts.append(1)
        raise OSError("no session bus")

    async def scenario() -> None:
        controls = MprisMediaControls(bus_factory=connect)
        controls.update(PLAYING)
        await asyncio.sleep(0)
        controls.update(None)
        controls.update(PLAYING)
        await asyncio.sleep(0)
        controls.close()

    asyncio.run(scenario())

    assert attempts == [1]
