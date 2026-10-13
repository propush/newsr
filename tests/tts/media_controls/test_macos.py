from __future__ import annotations

import pytest

from newsr.tts.media_controls import MediaCommand, NowPlaying, PlaybackStatus
from newsr.tts.media_controls import macos
from newsr.tts.media_controls.macos import SKIP_INTERVAL_SECONDS, MacMediaControls

from tests.tts.media_controls.fakes import FakeSeekEvent, NativeValue, install_fake_macos_modules

PLAYING = NowPlaying(title="Title 1", artist="BBC News", status=PlaybackStatus.PLAYING)


def test_mac_media_controls_publish_now_playing_and_forward_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install_fake_macos_modules(monkeypatch)
    received: list[MediaCommand] = []
    controls = MacMediaControls()
    controls.start(received.append)

    controls.update(PLAYING)

    assert fake.info.info == {
        "title": NativeValue("Title 1"),
        "artist": NativeValue("BBC News"),
        "albumTitle": NativeValue("NewsR"),
        "playbackRate": NativeValue(1.0),
    }
    assert fake.info.state == 1
    assert all(command.enabled and len(command.handlers) == 1 for command in fake.commands.values())
    assert fake.commands["skipForwardCommand"].preferred_intervals == [SKIP_INTERVAL_SECONDS]

    assert fake.commands["togglePlayPauseCommand"].fire() == [0]
    fake.commands["playCommand"].fire()
    fake.commands["pauseCommand"].fire()
    fake.commands["stopCommand"].fire()
    fake.commands["nextTrackCommand"].fire()
    fake.commands["previousTrackCommand"].fire()
    fake.commands["skipForwardCommand"].fire()
    fake.commands["skipBackwardCommand"].fire()
    fake.commands["seekForwardCommand"].fire(FakeSeekEvent(0))
    fake.commands["seekForwardCommand"].fire(FakeSeekEvent(1))
    fake.commands["seekBackwardCommand"].fire(FakeSeekEvent(0))

    assert received == [
        MediaCommand.TOGGLE,
        MediaCommand.PLAY,
        MediaCommand.PAUSE,
        MediaCommand.STOP,
        MediaCommand.NEXT,
        MediaCommand.PREVIOUS,
        MediaCommand.SEEK_FORWARD,
        MediaCommand.SEEK_BACKWARD,
        MediaCommand.SEEK_FORWARD,
        MediaCommand.SEEK_BACKWARD,
    ]


def test_mac_media_controls_pause_and_release_the_session(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install_fake_macos_modules(monkeypatch)
    controls = MacMediaControls()
    controls.start(lambda _command: None)

    controls.update(PLAYING)
    controls.update(NowPlaying(title="Title 1", artist="BBC News", status=PlaybackStatus.PAUSED))

    assert fake.info.state == 2
    assert fake.info.info is not None and fake.info.info["playbackRate"] == NativeValue(0.0)
    assert all(len(command.handlers) == 1 for command in fake.commands.values())

    controls.update(None)

    assert fake.info.info is None
    assert fake.info.state == 3
    assert all(not command.enabled and not command.handlers for command in fake.commands.values())
    controls.close()
    assert fake.info.state == 3


def test_mac_media_controls_pump_services_pending_run_loop_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install_fake_macos_modules(monkeypatch, run_loop_results=[4, 4, 1, 4])
    controls = MacMediaControls()

    controls.pump()

    assert fake.run_loop_calls == [("kCFRunLoopDefaultMode", 0, True)] * 3
    assert controls.pump_interval is not None


def test_mac_media_controls_show_the_session_under_the_launching_app_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install_fake_macos_modules(monkeypatch, parent_application="com.apple.Terminal")
    controls = MacMediaControls()

    controls.update(PLAYING)
    controls.update(None)
    controls.update(PLAYING)

    assert fake.parents == ["com.apple.Terminal"]


def test_mac_media_controls_skip_the_parent_app_without_a_launching_app(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install_fake_macos_modules(monkeypatch)
    controls = MacMediaControls()

    controls.update(PLAYING)

    assert fake.parents == []
    assert fake.info.state == 1


def test_mac_media_controls_keep_working_when_the_parent_app_cannot_be_set(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install_fake_macos_modules(monkeypatch, parent_application="com.apple.Terminal")

    def unavailable(_bundle_id: str) -> None:
        raise AttributeError("MRMediaRemoteSetParentApplication")

    monkeypatch.setattr(macos, "set_parent_application", unavailable)
    controls = MacMediaControls()

    controls.update(PLAYING)

    assert fake.info.state == 1
    assert all(len(command.handlers) == 1 for command in fake.commands.values())
