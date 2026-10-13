from __future__ import annotations

import ctypes
import os
from collections.abc import Callable
from typing import Any

from ...providers.tts.base import LOGGER, configure_tts_logger
from .base import ALBUM_TITLE, CommandHandler, MediaCommand, NowPlaying, PlaybackStatus

SKIP_INTERVAL_SECONDS = 15.0
PARENT_APPLICATION_ENV = "__CFBundleIdentifier"
_PUMP_SECONDS = 0.1
_MAX_PUMPED_SOURCES = 16
_MEDIA_REMOTE = "/System/Library/PrivateFrameworks/MediaRemote.framework/MediaRemote"
_CORE_FOUNDATION = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
_UTF8_ENCODING = 0x08000100


def set_parent_application(bundle_id: str) -> None:
    """Attribute the Now Playing session of this process to another app.

    Python has no app identity of its own, so macOS routes media keys to it but leaves it out of the
    Now Playing panel. WebKit uses this private MediaRemote call for its helper processes.
    """
    media_remote = ctypes.CDLL(_MEDIA_REMOTE)
    core_foundation = ctypes.CDLL(_CORE_FOUNDATION)
    core_foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
    core_foundation.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
    core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
    media_remote.MRMediaRemoteGetLocalOrigin.restype = ctypes.c_void_p
    media_remote.MRMediaRemoteSetParentApplication.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    media_remote.MRMediaRemoteSetParentApplication.restype = None
    name = core_foundation.CFStringCreateWithCString(None, bundle_id.encode(), _UTF8_ENCODING)
    try:
        media_remote.MRMediaRemoteSetParentApplication(media_remote.MRMediaRemoteGetLocalOrigin(), name)
    finally:
        core_foundation.CFRelease(name)


class MacMediaControls:
    """macOS Now Playing session.

    Remote commands reach the process through the main run loop, which Textual does not run, so
    `pump()` services it from the UI thread while a session is active. The session is shown under the
    app that started NewsR, usually the terminal, which macOS names in `__CFBundleIdentifier`.
    """

    pump_interval: float | None = _PUMP_SECONDS

    def __init__(self) -> None:
        import CoreFoundation
        import Foundation
        import MediaPlayer

        self._mp: Any = MediaPlayer
        self._cf: Any = CoreFoundation
        self._foundation: Any = Foundation
        self._handler: CommandHandler | None = None
        self._targets: list[tuple[Any, Any]] = []
        self._parent_checked = False

    def start(self, handler: CommandHandler) -> None:
        self._handler = handler

    def update(self, now_playing: NowPlaying | None) -> None:
        if now_playing is None:
            self._release()
            return
        if not self._targets:
            self._register()
        mp = self._mp
        playing = now_playing.status is PlaybackStatus.PLAYING
        center = mp.MPNowPlayingInfoCenter.defaultCenter()
        center.setNowPlayingInfo_(self._native_info(now_playing, rate=1.0 if playing else 0.0))
        center.setPlaybackState_(
            mp.MPNowPlayingPlaybackStatePlaying if playing else mp.MPNowPlayingPlaybackStatePaused
        )

    def pump(self) -> None:
        cf = self._cf
        for _ in range(_MAX_PUMPED_SOURCES):
            if cf.CFRunLoopRunInMode(cf.kCFRunLoopDefaultMode, 0, True) != cf.kCFRunLoopRunHandledSource:
                return

    def close(self) -> None:
        self._release()

    def _native_info(self, now_playing: NowPlaying, *, rate: float) -> Any:
        # MediaRemote reads this dictionary on its own queues, possibly while Python shuts down, so it
        # must hold native Foundation objects; Python-backed proxies would call back into Python.
        foundation = self._foundation
        mp = self._mp
        info = foundation.NSMutableDictionary.dictionary()
        for key, text in (
            (mp.MPMediaItemPropertyTitle, now_playing.title),
            (mp.MPMediaItemPropertyArtist, now_playing.artist),
            (mp.MPMediaItemPropertyAlbumTitle, ALBUM_TITLE),
        ):
            info.setObject_forKey_(foundation.NSString.stringWithString_(text), key)
        info.setObject_forKey_(foundation.NSNumber.numberWithDouble_(rate), mp.MPNowPlayingInfoPropertyPlaybackRate)
        return info

    def _register(self) -> None:
        self._present_under_parent_application()
        center = self._mp.MPRemoteCommandCenter.sharedCommandCenter()
        center.skipForwardCommand().setPreferredIntervals_([SKIP_INTERVAL_SECONDS])
        center.skipBackwardCommand().setPreferredIntervals_([SKIP_INTERVAL_SECONDS])
        bindings = (
            (center.togglePlayPauseCommand(), MediaCommand.TOGGLE, False),
            (center.playCommand(), MediaCommand.PLAY, False),
            (center.pauseCommand(), MediaCommand.PAUSE, False),
            (center.stopCommand(), MediaCommand.STOP, False),
            (center.nextTrackCommand(), MediaCommand.NEXT, False),
            (center.previousTrackCommand(), MediaCommand.PREVIOUS, False),
            (center.skipForwardCommand(), MediaCommand.SEEK_FORWARD, False),
            (center.skipBackwardCommand(), MediaCommand.SEEK_BACKWARD, False),
            (center.seekForwardCommand(), MediaCommand.SEEK_FORWARD, True),
            (center.seekBackwardCommand(), MediaCommand.SEEK_BACKWARD, True),
        )
        for command, media_command, seek in bindings:
            command.setEnabled_(True)
            target = command.addTargetWithHandler_(self._command_handler(media_command, seek=seek))
            self._targets.append((command, target))

    def _present_under_parent_application(self) -> None:
        if self._parent_checked:
            return
        self._parent_checked = True
        bundle_id = os.environ.get(PARENT_APPLICATION_ENV, "").strip()
        if not bundle_id:
            return
        try:
            set_parent_application(bundle_id)
        except (OSError, AttributeError) as exc:
            configure_tts_logger()
            LOGGER.warning(
                "media_controls_parent_application_failed bundle_id=%s error_type=%s error=%s",
                bundle_id,
                type(exc).__name__,
                exc,
            )

    def _command_handler(self, command: MediaCommand, *, seek: bool) -> Callable[[Any], int]:
        def handle(event: Any) -> int:
            # Holding a headset button sends one event when seeking starts and one when it ends.
            if seek and event.type() != self._mp.MPSeekCommandEventTypeBeginSeeking:
                return self._mp.MPRemoteCommandHandlerStatusSuccess
            handler = self._handler
            if handler is not None:
                handler(command)
            return self._mp.MPRemoteCommandHandlerStatusSuccess

        return handle

    def _release(self) -> None:
        if not self._targets:
            return
        for command, target in self._targets:
            command.removeTarget_(target)
            command.setEnabled_(False)
        self._targets = []
        center = self._mp.MPNowPlayingInfoCenter.defaultCenter()
        center.setNowPlayingInfo_(None)
        center.setPlaybackState_(self._mp.MPNowPlayingPlaybackStateStopped)
