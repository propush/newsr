from __future__ import annotations

from urllib.parse import quote

from ...cancellation import RefreshCancellation
from ...config.models import TTSElevenLabsConfig
from .base import SynthesizedAudio, TTSEngineError
from .http import post_for_bytes
from .voices import resolve_voice

MIN_ELEVENLABS_SPEED = 0.7
MAX_ELEVENLABS_SPEED = 1.2


class ElevenLabsTTSEngine:
    name = "elevenlabs"
    max_chars = 4500

    def __init__(
        self,
        config: TTSElevenLabsConfig,
        *,
        speed: float,
        request_retries: int,
        post=post_for_bytes,
    ) -> None:
        self._config = config
        self._speed = min(MAX_ELEVENLABS_SPEED, max(MIN_ELEVENLABS_SPEED, speed))
        self._request_retries = request_retries
        self._post = post

    def synthesize(
        self,
        text: str,
        language: str | None,
        cancellation: RefreshCancellation | None = None,
    ) -> SynthesizedAudio:
        voice_id = resolve_voice(self._config.voices, language)
        if not voice_id:
            raise TTSEngineError("tts.elevenlabs.voices.default is not configured")
        if not self._config.api_key:
            raise TTSEngineError("tts.elevenlabs.api_key is not configured")
        payload = {
            "text": text,
            "model_id": self._config.model,
            "voice_settings": {"speed": self._speed},
        }
        data = self._post(
            f"{self._config.url}/text-to-speech/{quote(voice_id, safe='')}?output_format=mp3_44100_128",
            payload,
            engine=self.name,
            headers={"xi-api-key": self._config.api_key, "Accept": "audio/mpeg"},
            request_retries=self._request_retries,
            cancellation=cancellation,
        )
        return SynthesizedAudio(data=data, format="mp3")
