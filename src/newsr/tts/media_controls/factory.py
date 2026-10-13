from __future__ import annotations

import sys

from ...providers.tts.base import LOGGER, configure_tts_logger
from .base import MediaControls, NullMediaControls


def build_media_controls(enabled: bool) -> MediaControls:
    """Build the media session of this platform, or a no-op one when it is disabled or unavailable."""
    if not enabled:
        return NullMediaControls()
    try:
        if sys.platform == "darwin":
            from .macos import MacMediaControls

            return MacMediaControls()
        if sys.platform.startswith("linux"):
            from .mpris import MprisMediaControls

            return MprisMediaControls()
        if sys.platform == "win32":
            from .windows import WindowsMediaControls

            return WindowsMediaControls()
    except Exception as exc:
        configure_tts_logger()
        LOGGER.warning(
            "media_controls_unavailable platform=%s error_type=%s error=%s",
            sys.platform,
            type(exc).__name__,
            exc,
        )
    return NullMediaControls()
