from __future__ import annotations

from typing import Any

from .models import (
    TTS_ENGINES,
    DEFAULT_TTS_ENGINE,
    TTSConfig,
    TTSEdgeConfig,
    TTSElevenLabsConfig,
    TTSOpenAIConfig,
    TTSPiperConfig,
    TTSSileroConfig,
    TTSSystemConfig,
)

MIN_TTS_SPEED = 0.5
MAX_TTS_SPEED = 2.0


def load_tts(raw: object) -> TTSConfig:
    raw = _mapping(raw, "tts")
    engine = str(raw.get("engine", DEFAULT_TTS_ENGINE)).strip().lower()
    if engine not in TTS_ENGINES:
        raise ValueError(f"tts.engine must be one of: {', '.join(TTS_ENGINES)}")
    speed = _load_speed(raw.get("speed", 1.0))
    original_language = str(raw.get("original_language", "en")).strip().lower()
    if not original_language:
        raise ValueError("tts.original_language must be a non-empty language code")
    request_retries = _load_int(raw.get("request_retries", 2), "tts.request_retries")
    if request_retries < 0:
        raise ValueError("tts.request_retries must be non-negative")
    media_controls = _load_bool(raw.get("media_controls", True), "tts.media_controls")
    config = TTSConfig(
        engine=engine,
        speed=speed,
        original_language=original_language,
        request_retries=request_retries,
        media_controls=media_controls,
        openai=_load_openai(_mapping(raw.get("openai"), "tts.openai")),
        elevenlabs=_load_elevenlabs(_mapping(raw.get("elevenlabs"), "tts.elevenlabs")),
        edge=TTSEdgeConfig(voices=_load_voices(_mapping(raw.get("edge"), "tts.edge"), "tts.edge")),
        piper=_load_piper(_mapping(raw.get("piper"), "tts.piper")),
        system=TTSSystemConfig(voices=_load_voices(_mapping(raw.get("system"), "tts.system"), "tts.system")),
        silero=_load_silero(_mapping(raw.get("silero"), "tts.silero")),
    )
    if engine == "elevenlabs":
        if not config.elevenlabs.api_key:
            raise ValueError("tts.elevenlabs.api_key is required when tts.engine is elevenlabs")
        if "default" not in config.elevenlabs.voices:
            raise ValueError("tts.elevenlabs.voices.default is required when tts.engine is elevenlabs")
    return config


def _load_openai(raw: dict) -> TTSOpenAIConfig:
    defaults = TTSOpenAIConfig()
    url = str(raw.get("url", defaults.url)).strip().rstrip("/")
    model = str(raw.get("model", defaults.model)).strip()
    if not url:
        raise ValueError("tts.openai.url must be non-empty")
    if not model:
        raise ValueError("tts.openai.model must be non-empty")
    return TTSOpenAIConfig(
        url=url,
        model=model,
        api_key=_load_optional_string(raw.get("api_key")),
        headers=_load_string_map(raw.get("headers"), "tts.openai.headers"),
        voices=_load_voices(raw, "tts.openai"),
    )


def _load_elevenlabs(raw: dict) -> TTSElevenLabsConfig:
    defaults = TTSElevenLabsConfig()
    url = str(raw.get("url", defaults.url)).strip().rstrip("/")
    model = str(raw.get("model", defaults.model)).strip()
    if not url:
        raise ValueError("tts.elevenlabs.url must be non-empty")
    if not model:
        raise ValueError("tts.elevenlabs.model must be non-empty")
    return TTSElevenLabsConfig(
        url=url,
        model=model,
        api_key=_load_optional_string(raw.get("api_key")),
        voices=_load_voices(raw, "tts.elevenlabs"),
    )


def _load_piper(raw: dict) -> TTSPiperConfig:
    models_dir = str(raw.get("models_dir", TTSPiperConfig().models_dir)).strip()
    if not models_dir:
        raise ValueError("tts.piper.models_dir must be non-empty")
    return TTSPiperConfig(models_dir=models_dir, voices=_load_voices(raw, "tts.piper"))


def _load_silero(raw: dict) -> TTSSileroConfig:
    models_dir = str(raw.get("models_dir", TTSSileroConfig().models_dir)).strip()
    if not models_dir:
        raise ValueError("tts.silero.models_dir must be non-empty")
    return TTSSileroConfig(
        models_dir=models_dir,
        voices=_load_voices(raw, "tts.silero"),
        lexicon=_load_string_map(raw.get("lexicon"), "tts.silero.lexicon"),
    )


def _load_voices(raw: dict, section: str) -> dict[str, str]:
    voices = _load_string_map(raw.get("voices"), f"{section}.voices")
    return {language.lower(): voice for language, voice in voices.items()}


def _load_speed(value: Any) -> float:
    try:
        speed = float(value)
    except (TypeError, ValueError):
        raise ValueError("tts.speed must be a number") from None
    if not MIN_TTS_SPEED <= speed <= MAX_TTS_SPEED:
        raise ValueError(f"tts.speed must be between {MIN_TTS_SPEED} and {MAX_TTS_SPEED}")
    return speed


def _load_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer") from None


def _load_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be true or false")


def _mapping(value: object, field_name: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    return value


def _load_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _load_string_map(value: Any, field_name: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    result: dict[str, str] = {}
    for key, item in value.items():
        name = "" if key is None else str(key).strip()
        text = "" if item is None else str(item).strip()
        if not name or not text:
            raise ValueError(f"{field_name} keys and values must be non-empty strings")
        result[name] = text
    return result
