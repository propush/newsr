from __future__ import annotations

import io
import json
import re
import wave
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any

from ...cancellation import RefreshCancellation, RefreshCancelled, cancellable_read
from ...config.models import TTSPiperConfig
from ..transport import build_request, newsr_headers, open_request
from .base import LOGGER, SynthesizedAudio, TTSEngineError, configure_tts_logger
from .voices import preferred_locale

DEFAULT_PIPER_VOICE = "en_US-lessac-medium"
PIPER_VOICES_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
VOICES_INDEX_NAME = "voices.json"
DOWNLOAD_TIMEOUT_SECONDS = 300
_VOICE_PATTERN = re.compile(
    r"^(?P<family>[^-_]+)_(?P<region>[^-]+)-(?P<name>[^-]+)-(?P<quality>.+)$"
)

Fetcher = Callable[[str, RefreshCancellation | None], bytes]
VoiceLoader = Callable[[Path], Any]


def _fetch(url: str, cancellation: RefreshCancellation | None) -> bytes:
    request = build_request(url, headers=newsr_headers())
    with open_request(request, cancellation, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return cancellable_read(response, cancellation)


def _load_piper_voice(model_path: Path) -> Any:
    from piper import PiperVoice

    return PiperVoice.load(model_path)


def _synthesis_config(length_scale: float) -> Any:
    from piper import SynthesisConfig

    return SynthesisConfig(length_scale=length_scale)


def voice_file_url(voice: str, extension: str) -> str:
    match = _VOICE_PATTERN.match(voice)
    if match is None:
        raise TTSEngineError(
            f"piper voice '{voice}' must look like <language>_<REGION>-<name>-<quality>, e.g. {DEFAULT_PIPER_VOICE}"
        )
    family = match.group("family")
    lang_code = f"{family}_{match.group('region')}"
    return (
        f"{PIPER_VOICES_URL}/{family}/{lang_code}/{match.group('name')}/{match.group('quality')}/"
        f"{voice}{extension}?download=true"
    )


class PiperTTSEngine:
    name = "piper"
    max_chars = 1000

    def __init__(
        self,
        config: TTSPiperConfig,
        *,
        speed: float,
        fetch: Fetcher = _fetch,
        voice_loader: VoiceLoader = _load_piper_voice,
        synthesis_config: Callable[[float], Any] = _synthesis_config,
    ) -> None:
        self._config = config
        self._models_dir = Path(config.models_dir)
        self._length_scale = 1.0 / speed
        self._fetch = fetch
        self._voice_loader = voice_loader
        self._synthesis_config = synthesis_config
        self._loaded: dict[str, Any] = {}
        self._index: dict[str, Any] | None = None
        self._lock = Lock()

    def synthesize(
        self,
        text: str,
        language: str | None,
        cancellation: RefreshCancellation | None = None,
    ) -> SynthesizedAudio:
        configure_tts_logger()
        with self._lock:
            voice_name = self.voice_for(language, cancellation)
            voice = self._voice(voice_name, cancellation)
        buffer = io.BytesIO()
        try:
            with wave.open(buffer, "wb") as wav_file:
                format_set = False
                for chunk in voice.synthesize(text, syn_config=self._synthesis_config(self._length_scale)):
                    if cancellation is not None:
                        cancellation.raise_if_cancelled()
                    if not format_set:
                        wav_file.setframerate(chunk.sample_rate)
                        wav_file.setsampwidth(chunk.sample_width)
                        wav_file.setnchannels(chunk.sample_channels)
                        format_set = True
                    wav_file.writeframes(chunk.audio_int16_bytes)
                if not format_set:
                    raise TTSEngineError("piper synthesis returned no audio")
        except (RefreshCancelled, TTSEngineError):
            raise
        except Exception as exc:
            LOGGER.error("synthesis_failed engine=piper voice=%s error_type=%s error=%s", voice_name, type(exc).__name__, exc)
            raise TTSEngineError(f"piper synthesis failed: {exc}") from exc
        return SynthesizedAudio(data=buffer.getvalue(), format="wav")

    def voice_for(self, language: str | None, cancellation: RefreshCancellation | None = None) -> str:
        voices = self._config.voices
        if language and language.lower() in voices:
            return voices[language.lower()]
        if language:
            discovered = self._discover_voice(language.lower(), cancellation)
            if discovered:
                return discovered
        return voices.get("default", DEFAULT_PIPER_VOICE)

    def _voice(self, voice_name: str, cancellation: RefreshCancellation | None) -> Any:
        loaded = self._loaded.get(voice_name)
        if loaded is not None:
            return loaded
        model_path = self._models_dir / f"{voice_name}.onnx"
        config_path = self._models_dir / f"{voice_name}.onnx.json"
        self._ensure_file(model_path, voice_file_url(voice_name, ".onnx"), cancellation)
        self._ensure_file(config_path, voice_file_url(voice_name, ".onnx.json"), cancellation)
        try:
            loaded = self._voice_loader(model_path)
        except Exception as exc:
            raise TTSEngineError(f"piper could not load voice {voice_name}: {exc}") from exc
        self._loaded[voice_name] = loaded
        return loaded

    def _discover_voice(self, language: str, cancellation: RefreshCancellation | None) -> str | None:
        index = self._voices_index(cancellation)
        preferred = preferred_locale(language)
        candidates = sorted(
            (
                str(entry.get("language", {}).get("code", "")) != preferred,
                entry.get("quality") != "medium",
                key,
            )
            for key, entry in index.items()
            if isinstance(entry, dict) and str(entry.get("language", {}).get("family", "")).lower() == language
        )
        return candidates[0][2] if candidates else None

    def _voices_index(self, cancellation: RefreshCancellation | None) -> dict[str, Any]:
        if self._index is not None:
            return self._index
        index_path = self._models_dir / VOICES_INDEX_NAME
        try:
            self._ensure_file(index_path, f"{PIPER_VOICES_URL}/{VOICES_INDEX_NAME}?download=true", cancellation)
            self._index = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TTSEngineError) as exc:
            LOGGER.warning("voice_index_failed engine=piper error_type=%s error=%s", type(exc).__name__, exc)
            return {}
        return self._index

    def _ensure_file(self, path: Path, url: str, cancellation: RefreshCancellation | None) -> None:
        if path.exists() and path.stat().st_size > 0:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        LOGGER.info("download_start engine=piper url=%s", url)
        try:
            data = self._fetch(url, cancellation)
        except RefreshCancelled:
            raise
        except Exception as exc:
            LOGGER.error("download_failed engine=piper url=%s error_type=%s error=%s", url, type(exc).__name__, exc)
            raise TTSEngineError(f"piper download failed for {path.name}: {exc}") from exc
        partial_path = path.with_name(f"{path.name}.part")
        partial_path.write_bytes(data)
        partial_path.replace(path)
        LOGGER.info("download_done engine=piper path=%s bytes=%s", path, len(data))
