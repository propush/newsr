from __future__ import annotations

import asyncio
from collections.abc import Callable

from newsr.domain import PlaylistItem
from newsr.tts import MediaCommand, NowPlaying, PlaybackStatus
from newsr.tts.media_controls import CommandHandler
from newsr.ui import NewsReaderApp
from newsr.ui.screens import PlaylistScreen

from tests.tts.fakes import FakeAudioOutput, FakeTTSEngine
from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article


class FakeMediaControls:
    def __init__(self, *, pump_interval: float | None = None, fail_on_update: bool = False) -> None:
        self.pump_interval = pump_interval
        self.fail_on_update = fail_on_update
        self.handler: CommandHandler | None = None
        self.updates: list[NowPlaying | None] = []
        self.pumps = 0
        self.closed = False

    def start(self, handler: CommandHandler) -> None:
        self.handler = handler

    def update(self, now_playing: NowPlaying | None) -> None:
        if self.fail_on_update:
            raise RuntimeError("media session unavailable")
        self.updates.append(now_playing)

    def pump(self) -> None:
        self.pumps += 1

    def close(self) -> None:
        self.closed = True

    @property
    def state(self) -> NowPlaying | None:
        return self.updates[-1] if self.updates else None

    def press(self, command: MediaCommand) -> None:
        assert self.handler is not None
        self.handler(command)


def build_app(app_config, tmp_path, media: FakeMediaControls, enabled_flags: list[bool] | None = None):
    output = FakeAudioOutput(auto_finish=False)

    def media_factory(enabled: bool) -> FakeMediaControls:
        if enabled_flags is not None:
            enabled_flags.append(enabled)
        return media

    app = NewsReaderApp(
        app_config,
        tmp_path / "newsr.sqlite3",
        audio_output_factory=lambda: output,
        tts_engine_factory=lambda _config: FakeTTSEngine(),
        media_controls_factory=media_factory,
    )
    disable_startup_refresh(app)
    article_ids = [
        seed_provider_article(
            app,
            provider_id="bbc",
            provider_article_id=f"bbc-{index}",
            title=f"Title {index}",
            body=f"Body {index}.",
            minute=index,
        )
        for index in (1, 2)
    ]
    return app, output, article_ids


async def wait_for(pilot, predicate: Callable[[], bool], *, attempts: int = 200) -> None:
    for _ in range(attempts):
        if predicate():
            return
        await pilot.pause(0.01)
    raise AssertionError("condition was not reached")


def now_playing(title: str, status: PlaybackStatus) -> NowPlaying:
    return NowPlaying(title=title, artist="BBC News", status=status)


def test_media_session_follows_playback_and_is_released_when_the_playlist_ends(app_config, tmp_path) -> None:
    media = FakeMediaControls()
    enabled_flags: list[bool] = []
    app, output, _article_ids = build_app(app_config, tmp_path, media, enabled_flags)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert media.handler is None
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: media.state == now_playing("Title 1", PlaybackStatus.PLAYING))
            assert enabled_flags == [app_config.tts.media_controls]

            await pilot.press("p")
            await wait_for(pilot, lambda: media.state == now_playing("Title 1", PlaybackStatus.PAUSED))
            await pilot.press("p")
            await wait_for(pilot, lambda: media.state == now_playing("Title 1", PlaybackStatus.PLAYING))

            output.release(3)
            await wait_for(pilot, lambda: media.state == now_playing("Title 2", PlaybackStatus.PLAYING))
            output.release(3)
            await wait_for(pilot, lambda: not app._playlist.is_running)
            assert media.state is None
            assert media.updates.count(None) == 1

    asyncio.run(runner())


def test_media_commands_drive_the_playlist(app_config, tmp_path) -> None:
    media = FakeMediaControls()
    app, output, article_ids = build_app(app_config, tmp_path, media)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 2."])

            media.press(MediaCommand.TOGGLE)
            await wait_for(pilot, lambda: output.paused)
            media.press(MediaCommand.PAUSE)
            media.press(MediaCommand.PLAY)
            await wait_for(pilot, lambda: not output.paused)
            media.press(MediaCommand.PLAY)
            media.press(MediaCommand.STOP)
            await wait_for(pilot, lambda: output.paused)
            media.press(MediaCommand.TOGGLE)
            await wait_for(pilot, lambda: not output.paused)

            media.press(MediaCommand.SEEK_FORWARD)
            await wait_for(pilot, lambda: output.played[-1:] == ["Title 1."])
            media.press(MediaCommand.SEEK_BACKWARD)
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 1 of 2."])

            media.press(MediaCommand.NEXT)
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 2 of 2."])
            assert app._playlist.items == [PlaylistItem(article_ids[1], "[ALL]")]

            media.press(MediaCommand.PREVIOUS)
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 1 of 2."])
            assert [item.article_id for item in app._playlist.items] == article_ids
            assert app.storage.load_playlist() == app._playlist.items

            media.press(MediaCommand.SEEK_FORWARD)
            await wait_for(pilot, lambda: output.played[-1:] == ["Title 1."])
            played = len(output.played)
            media.press(MediaCommand.PREVIOUS)
            await wait_for(pilot, lambda: len(output.played) == played + 1)
            assert output.played[-1] == "BBC News. Article 1 of 2."
            assert [item.article_id for item in app._playlist.items] == article_ids
            app._playlist.clear()

    asyncio.run(runner())


def test_media_navigation_commands_are_ignored_while_stopped(app_config, tmp_path) -> None:
    media = FakeMediaControls()
    app, output, article_ids = build_app(app_config, tmp_path, media)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 2."])
            app._playlist.cancel()
            await pilot.pause()

            for command in (MediaCommand.NEXT, MediaCommand.PREVIOUS, MediaCommand.SEEK_FORWARD, MediaCommand.PAUSE):
                app._playlist.handle_media_command(command)
            await pilot.pause()

            assert [item.article_id for item in app._playlist.items] == article_ids
            assert not app._playlist.is_running

    asyncio.run(runner())


def test_segment_keys_seek_within_the_article(app_config, tmp_path) -> None:
    media = FakeMediaControls()
    app, output, _article_ids = build_app(app_config, tmp_path, media)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 2."])

            await pilot.press("full_stop")
            await wait_for(pilot, lambda: output.played[-1:] == ["Title 1."])
            await pilot.press("full_stop")
            await wait_for(pilot, lambda: output.played[-1:] == ["Body 1."])
            output.elapsed = 5.0
            await pilot.press("comma")
            await wait_for(pilot, lambda: len(output.played) == 4)
            assert output.played[-1] == "Body 1."
            output.elapsed = 0.0
            await pilot.press("comma")
            await wait_for(pilot, lambda: output.played[-1:] == ["Title 1."])

            await pilot.press("P")
            await wait_for(pilot, lambda: isinstance(app.screen, PlaylistScreen))
            await pilot.press("full_stop")
            await wait_for(pilot, lambda: output.played[-1:] == ["Body 1."])
            await pilot.press("comma")
            await wait_for(pilot, lambda: output.played[-1:] == ["Title 1."])
            await pilot.press("left_square_bracket")
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 1 of 2."])
            app._playlist.clear()

    asyncio.run(runner())


def test_media_session_pump_runs_only_while_the_session_is_active(app_config, tmp_path) -> None:
    media = FakeMediaControls(pump_interval=0.01)
    app, output, _article_ids = build_app(app_config, tmp_path, media)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: media.pumps >= 3)

            app._playlist.clear()
            await wait_for(pilot, lambda: media.state is None)
            pumps = media.pumps
            await pilot.pause(0.1)
            assert media.pumps == pumps

        assert media.closed

    asyncio.run(runner())


def test_media_session_errors_do_not_stop_playback(app_config, tmp_path) -> None:
    media = FakeMediaControls(fail_on_update=True)
    app, output, _article_ids = build_app(app_config, tmp_path, media)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 2."])
            assert media.closed
            output.release()
            await wait_for(pilot, lambda: output.played[-1:] == ["Title 1."])
            assert app._playlist.is_playing
            app._playlist.clear()

    asyncio.run(runner())
