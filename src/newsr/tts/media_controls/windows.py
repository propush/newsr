from __future__ import annotations

from typing import Any

from .base import ALBUM_TITLE, CommandHandler, MediaCommand, NowPlaying, PlaybackStatus


class WindowsMediaControls:
    """Windows System Media Transport Controls, reached through a `MediaPlayer` that plays nothing."""

    pump_interval: float | None = None

    def __init__(self) -> None:
        from winrt.windows import media
        from winrt.windows.media.playback import MediaPlayer

        self._media: Any = media
        self._player: Any = MediaPlayer()
        self._player.command_manager.is_enabled = False
        self._controls: Any = self._player.system_media_transport_controls
        buttons = media.SystemMediaTransportControlsButton
        self._commands = {
            buttons.PLAY: MediaCommand.PLAY,
            buttons.PAUSE: MediaCommand.PAUSE,
            buttons.STOP: MediaCommand.STOP,
            buttons.NEXT: MediaCommand.NEXT,
            buttons.PREVIOUS: MediaCommand.PREVIOUS,
            buttons.FAST_FORWARD: MediaCommand.SEEK_FORWARD,
            buttons.REWIND: MediaCommand.SEEK_BACKWARD,
        }
        self._handler: CommandHandler | None = None
        self._token: Any = None

    def start(self, handler: CommandHandler) -> None:
        self._handler = handler

    def update(self, now_playing: NowPlaying | None) -> None:
        controls = self._controls
        if now_playing is None:
            self._release()
            return
        if self._token is None:
            for name in ("play", "pause", "stop", "next", "previous", "fast_forward", "rewind"):
                setattr(controls, f"is_{name}_enabled", True)
            self._token = controls.add_button_pressed(self._button_pressed)
            controls.is_enabled = True
        status = self._media.MediaPlaybackStatus
        controls.playback_status = (
            status.PLAYING if now_playing.status is PlaybackStatus.PLAYING else status.PAUSED
        )
        updater = controls.display_updater
        updater.type = self._media.MediaPlaybackType.MUSIC
        updater.music_properties.title = now_playing.title
        updater.music_properties.artist = now_playing.artist
        updater.music_properties.album_title = ALBUM_TITLE
        updater.update()

    def pump(self) -> None:
        return

    def close(self) -> None:
        self._release()
        self._player.close()

    def _button_pressed(self, _sender: Any, args: Any) -> None:
        command = self._commands.get(args.button)
        handler = self._handler
        if command is not None and handler is not None:
            handler(command)

    def _release(self) -> None:
        if self._token is None:
            return
        controls = self._controls
        controls.remove_button_pressed(self._token)
        self._token = None
        controls.playback_status = self._media.MediaPlaybackStatus.STOPPED
        updater = controls.display_updater
        updater.clear_all()
        updater.update()
        controls.is_enabled = False
