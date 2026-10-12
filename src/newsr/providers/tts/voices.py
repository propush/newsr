from __future__ import annotations

from collections.abc import Mapping

_PREFERRED_REGIONS = {
    "cs": "CZ", "da": "DK", "el": "GR", "en": "US", "he": "IL", "hi": "IN",
    "ja": "JP", "ko": "KR", "pt": "BR", "sv": "SE", "uk": "UA", "zh": "CN",
}


def resolve_voice(voices: Mapping[str, str], language: str | None) -> str | None:
    if language:
        voice = voices.get(language.lower())
        if voice:
            return voice
    return voices.get("default")


def preferred_locale(language: str, *, separator: str = "_") -> str:
    language = language.lower()
    return f"{language}{separator}{_PREFERRED_REGIONS.get(language, language.upper())}"


def speed_percent(speed: float) -> int:
    return round((speed - 1.0) * 100)
