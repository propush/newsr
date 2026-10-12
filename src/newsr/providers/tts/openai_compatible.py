from __future__ import annotations

from ...cancellation import RefreshCancellation
from ...config.models import TTSOpenAIConfig
from .base import SynthesizedAudio
from .http import post_for_bytes
from .voices import resolve_voice

DEFAULT_OPENAI_VOICE = "alloy"


class OpenAICompatibleTTSEngine:
    name = "openai"
    max_chars = 4000

    def __init__(self, config: TTSOpenAIConfig, *, speed: float, request_retries: int, post=post_for_bytes) -> None:
        self._config = config
        self._speed = speed
        self._request_retries = request_retries
        self._post = post

    def synthesize(
        self,
        text: str,
        language: str | None,
        cancellation: RefreshCancellation | None = None,
    ) -> SynthesizedAudio:
        payload = {
            "model": self._config.model,
            "input": text,
            "voice": resolve_voice(self._config.voices, language) or DEFAULT_OPENAI_VOICE,
            "response_format": "mp3",
            "speed": self._speed,
        }
        data = self._post(
            f"{self._config.url}/audio/speech",
            payload,
            engine=self.name,
            headers=self._headers(),
            request_retries=self._request_retries,
            cancellation=cancellation,
        )
        return SynthesizedAudio(data=data, format="mp3")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        headers.update(self._config.headers)
        return headers
