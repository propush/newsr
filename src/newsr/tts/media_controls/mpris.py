from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from dbus_fast import BusType, PropertyAccess, Variant
from dbus_fast.annotations import DBusBool, DBusDict, DBusDouble, DBusInt64, DBusObjectPath, DBusSignature, DBusStr
from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface, dbus_property, method

from ...providers.tts.base import LOGGER, configure_tts_logger
from .base import ALBUM_TITLE, CommandHandler, MediaCommand, NowPlaying, PlaybackStatus

OBJECT_PATH = "/org/mpris/MediaPlayer2"
NO_TRACK = "/org/mpris/MediaPlayer2/TrackList/NoTrack"
DBusStrList = Annotated[list[str], DBusSignature("as")]
BusFactory = Callable[[], Awaitable[Any]]


async def _connect_session_bus() -> MessageBus:
    return await MessageBus(bus_type=BusType.SESSION).connect()


class _RootInterface(ServiceInterface):
    def __init__(self) -> None:
        super().__init__("org.mpris.MediaPlayer2")

    @method()
    def Raise(self):  # noqa: N802
        return

    @method()
    def Quit(self):  # noqa: N802
        return

    @dbus_property(access=PropertyAccess.READ)
    def CanQuit(self) -> DBusBool:  # noqa: N802
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanRaise(self) -> DBusBool:  # noqa: N802
        return False

    @dbus_property(access=PropertyAccess.READ)
    def HasTrackList(self) -> DBusBool:  # noqa: N802
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> DBusStr:  # noqa: N802
        return ALBUM_TITLE

    @dbus_property(access=PropertyAccess.READ)
    def SupportedUriSchemes(self) -> DBusStrList:  # noqa: N802
        return []

    @dbus_property(access=PropertyAccess.READ)
    def SupportedMimeTypes(self) -> DBusStrList:  # noqa: N802
        return []


class PlayerInterface(ServiceInterface):
    """The `org.mpris.MediaPlayer2.Player` interface that desktop media keys and headsets talk to."""

    def __init__(self, emit: Callable[[MediaCommand], None]) -> None:
        super().__init__("org.mpris.MediaPlayer2.Player")
        self._emit = emit
        self._status = "Stopped"
        self._metadata: dict[str, Variant] = {"mpris:trackid": Variant("o", NO_TRACK)}
        self._track_number = 0
        self._title: str | None = None

    def set_now_playing(self, now_playing: NowPlaying | None) -> None:
        if now_playing is None:
            status = "Stopped"
            self._title = None
            metadata = {"mpris:trackid": Variant("o", NO_TRACK)}
        else:
            status = "Playing" if now_playing.status is PlaybackStatus.PLAYING else "Paused"
            if now_playing.title != self._title:
                self._title = now_playing.title
                self._track_number += 1
            metadata = {
                "mpris:trackid": Variant("o", f"/org/newsr/track/{self._track_number}"),
                "xesam:title": Variant("s", now_playing.title),
                "xesam:artist": Variant("as", [now_playing.artist]),
                "xesam:album": Variant("s", ALBUM_TITLE),
            }
        changed: dict[str, Any] = {}
        if status != self._status:
            self._status = status
            changed["PlaybackStatus"] = status
        if metadata != self._metadata:
            self._metadata = metadata
            changed["Metadata"] = metadata
        if changed:
            self.emit_properties_changed(changed)

    @method()
    def Next(self):  # noqa: N802
        self._emit(MediaCommand.NEXT)

    @method()
    def Previous(self):  # noqa: N802
        self._emit(MediaCommand.PREVIOUS)

    @method()
    def Pause(self):  # noqa: N802
        self._emit(MediaCommand.PAUSE)

    @method()
    def PlayPause(self):  # noqa: N802
        self._emit(MediaCommand.TOGGLE)

    @method()
    def Stop(self):  # noqa: N802
        self._emit(MediaCommand.STOP)

    @method()
    def Play(self):  # noqa: N802
        self._emit(MediaCommand.PLAY)

    @method()
    def Seek(self, offset: DBusInt64):  # noqa: N802
        if offset > 0:
            self._emit(MediaCommand.SEEK_FORWARD)
        elif offset < 0:
            self._emit(MediaCommand.SEEK_BACKWARD)

    @method()
    def SetPosition(self, track_id: DBusObjectPath, position: DBusInt64):  # noqa: N802
        return

    @method()
    def OpenUri(self, uri: DBusStr):  # noqa: N802
        return

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> DBusStr:  # noqa: N802
        return self._status

    @dbus_property(access=PropertyAccess.READ)
    def Rate(self) -> DBusDouble:  # noqa: N802
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MinimumRate(self) -> DBusDouble:  # noqa: N802
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def MaximumRate(self) -> DBusDouble:  # noqa: N802
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> DBusDict:  # noqa: N802
        return self._metadata

    @dbus_property(access=PropertyAccess.READ)
    def Volume(self) -> DBusDouble:  # noqa: N802
        return 1.0

    @dbus_property(access=PropertyAccess.READ)
    def Position(self) -> DBusInt64:  # noqa: N802
        return 0

    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> DBusBool:  # noqa: N802
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> DBusBool:  # noqa: N802
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> DBusBool:  # noqa: N802
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> DBusBool:  # noqa: N802
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanSeek(self) -> DBusBool:  # noqa: N802
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> DBusBool:  # noqa: N802
        return True


class MprisMediaControls:
    """MPRIS player on the D-Bus session bus; it owns its bus name only while a session is active."""

    pump_interval: float | None = None

    def __init__(self, bus_factory: BusFactory = _connect_session_bus) -> None:
        self._bus_factory = bus_factory
        self._bus_name = f"org.mpris.MediaPlayer2.newsr.instance{os.getpid()}"
        self._handler: CommandHandler | None = None
        self._root = _RootInterface()
        self.player = PlayerInterface(self._emit)
        self._bus: Any = None
        self._owned = False
        self._active = False
        self._failed = False
        self._task: asyncio.Task[None] | None = None

    def start(self, handler: CommandHandler) -> None:
        self._handler = handler

    def update(self, now_playing: NowPlaying | None) -> None:
        self.player.set_now_playing(now_playing)
        self._active = now_playing is not None
        if self._failed or self._active == self._owned:
            return
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._sync())

    def pump(self) -> None:
        return

    def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
        bus = self._bus
        self._bus = None
        self._owned = False
        if bus is not None:
            bus.disconnect()

    async def _sync(self) -> None:
        try:
            while self._active != self._owned:
                if self._active:
                    if self._bus is None:
                        bus = await self._bus_factory()
                        bus.export(OBJECT_PATH, self._root)
                        bus.export(OBJECT_PATH, self.player)
                        self._bus = bus
                    await self._bus.request_name(self._bus_name)
                    self._owned = True
                else:
                    await self._bus.release_name(self._bus_name)
                    self._owned = False
        except Exception as exc:
            self._failed = True
            configure_tts_logger()
            LOGGER.warning("media_controls_failed backend=mpris error_type=%s error=%s", type(exc).__name__, exc)

    def _emit(self, command: MediaCommand) -> None:
        handler = self._handler
        if handler is not None:
            handler(command)
