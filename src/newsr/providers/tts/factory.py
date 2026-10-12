from __future__ import annotations

from ...config.models import TTSConfig
from .base import TransliterationLLM, TTSEngine, TTSEngineError


def build_tts_engine(config: TTSConfig, *, llm: TransliterationLLM | None = None) -> TTSEngine:
    if config.engine == "openai":
        from .openai_compatible import OpenAICompatibleTTSEngine

        return OpenAICompatibleTTSEngine(config.openai, speed=config.speed, request_retries=config.request_retries)
    if config.engine == "elevenlabs":
        from .elevenlabs import ElevenLabsTTSEngine

        return ElevenLabsTTSEngine(config.elevenlabs, speed=config.speed, request_retries=config.request_retries)
    if config.engine == "edge":
        from .edge import EdgeTTSEngine

        return EdgeTTSEngine(config.edge, speed=config.speed)
    if config.engine == "piper":
        from .piper import PiperTTSEngine

        return PiperTTSEngine(config.piper, speed=config.speed)
    if config.engine == "system":
        from .system import SystemTTSEngine

        return SystemTTSEngine(config.system, speed=config.speed)
    if config.engine == "silero":
        from .silero import SileroTTSEngine

        return SileroTTSEngine(
            config.silero,
            speed=config.speed,
            llm_transliterate=llm.transliterate_terms if llm is not None else None,
        )
    raise TTSEngineError(f"unknown TTS engine: {config.engine}")
