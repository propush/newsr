from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Mapping
from threading import Lock

from ...cancellation import RefreshCancellation, RefreshCancelled
from ...config.models import TTSEdgeConfig
from .base import LOGGER, SynthesizedAudio, TTSEngineError, configure_tts_logger
from .voices import preferred_locale, resolve_voice, speed_percent

DEFAULT_EDGE_VOICE = "en-US-EmmaMultilingualNeural"

AudioStreamer = Callable[[str, str, str, RefreshCancellation | None], Iterable[Mapping[str, object]]]
VoiceLister = Callable[[], list[Mapping[str, object]]]


def _edge_stream(
    text: str,
    voice: str,
    rate: str,
    cancellation: RefreshCancellation | None,
) -> list[Mapping[str, object]]:
    import edge_tts

    async def collect() -> list[Mapping[str, object]]:
        chunks: list[Mapping[str, object]] = []
        async for chunk in edge_tts.Communicate(text, voice, rate=rate).stream():
            if cancellation is not None:
                cancellation.raise_if_cancelled()
            chunks.append(chunk)
        return chunks

    return asyncio.run(collect())


def _edge_list_voices() -> list[Mapping[str, object]]:
    import edge_tts

    return asyncio.run(edge_tts.list_voices())


class EdgeTTSEngine:
    name = "edge"
    max_chars = 3000

    def __init__(
        self,
        config: TTSEdgeConfig,
        *,
        speed: float,
        stream: AudioStreamer = _edge_stream,
        list_voices: VoiceLister = _edge_list_voices,
    ) -> None:
        self._config = config
        self._rate = f"{speed_percent(speed):+d}%"
        self._stream = stream
        self._list_voices = list_voices
        self._voices_by_language: dict[str, list[str]] | None = None
        self._silent_voices: set[str] = set()
        self._voices_lock = Lock()

    def synthesize(
        self,
        text: str,
        language: str | None,
        cancellation: RefreshCancellation | None = None,
    ) -> SynthesizedAudio:
        configure_tts_logger()
        for voice in self.candidate_voices(language):
            audio = self._synthesize_with(text, voice, cancellation)
            if audio is not None:
                return audio
            LOGGER.warning("no_audio engine=edge voice=%s text_chars=%s", voice, len(text))
            self._silent_voices.add(voice)
        raise TTSEngineError("edge synthesis returned no audio")

    def voice_for(self, language: str | None) -> str:
        return self.candidate_voices(language)[0]

    def candidate_voices(self, language: str | None) -> list[str]:
        if language and language.lower() in self._config.voices:
            return [self._config.voices[language.lower()]]
        candidates = self._discovered_voices().get(language.lower(), []) if language else []
        fallback = resolve_voice(self._config.voices, None) or DEFAULT_EDGE_VOICE
        ordered = [voice for voice in candidates if voice not in self._silent_voices]
        ordered += [voice for voice in candidates if voice in self._silent_voices]
        if fallback not in ordered:
            ordered.append(fallback)
        return ordered

    def _synthesize_with(
        self,
        text: str,
        voice: str,
        cancellation: RefreshCancellation | None,
    ) -> SynthesizedAudio | None:
        LOGGER.info("request_start engine=edge voice=%s text_chars=%s", voice, len(text))
        chunks: list[bytes] = []
        try:
            for chunk in self._stream(text, voice, self._rate, cancellation):
                if chunk.get("type") == "audio":
                    data = chunk.get("data")
                    if isinstance(data, bytes):
                        chunks.append(data)
        except RefreshCancelled:
            raise
        except Exception as exc:
            if type(exc).__name__ == "NoAudioReceived":
                return None
            LOGGER.error("request_failed engine=edge error_type=%s error=%s", type(exc).__name__, exc)
            raise TTSEngineError(f"edge synthesis failed: {exc}") from exc
        if not chunks:
            return None
        LOGGER.info("request_done engine=edge voice=%s bytes=%s", voice, sum(len(chunk) for chunk in chunks))
        return SynthesizedAudio(data=b"".join(chunks), format="mp3")

    def _discovered_voices(self) -> dict[str, list[str]]:
        with self._voices_lock:
            if self._voices_by_language is not None:
                return self._voices_by_language
            try:
                listed = self._list_voices()
            except Exception as exc:
                LOGGER.warning("voice_list_failed engine=edge error_type=%s error=%s", type(exc).__name__, exc)
                return {}
            preferred: dict[str, list[str]] = {}
            others: dict[str, list[str]] = {}
            for entry in listed:
                locale = str(entry.get("Locale", ""))
                short_name = str(entry.get("ShortName", ""))
                language = locale.split("-", 1)[0].lower()
                if not language or not short_name:
                    continue
                target = preferred if locale.lower() == preferred_locale(language, separator="-").lower() else others
                target.setdefault(language, []).append(short_name)
            voices = {
                language: preferred.get(language, []) + others.get(language, [])
                for language in {*preferred, *others}
            }
            self._voices_by_language = voices
            return voices
