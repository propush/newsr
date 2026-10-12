from __future__ import annotations

from ...config.models import TTSConfig
from .base import TTSEngine, TTSEngineError


def build_tts_engine(config: TTSConfig) -> TTSEngine:
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
    raise TTSEngineError(f"unknown TTS engine: {config.engine}")
