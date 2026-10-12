from __future__ import annotations

import importlib.util
import io
import re
import warnings
import wave
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any
from xml.sax.saxutils import escape

from ...cancellation import RefreshCancellation, RefreshCancelled, cancellable_read
from ...config.models import TTSSileroConfig
from ...tts.text import split_chunks
from ..transport import build_request, newsr_headers, open_request
from .base import LOGGER, SynthesizedAudio, TTSEngineError, configure_tts_logger

SAMPLE_RATE = 48000
DOWNLOAD_TIMEOUT_SECONDS = 600
PIECE_CHARS = 800
SENTENCE_PAUSE_SECONDS = 0.15
PARAGRAPH_PAUSE_SECONDS = 0.35
INSTALL_HINT = 'the silero engine needs extra packages: pip install -e ".[silero]"'
REQUIRED_MODULES = ("torch", "scipy", "numpy", "num2words", "pymorphy3", "transformers")
# Silero changes speed in five SSML steps; each threshold is the midpoint between neighbouring steps.
RATE_STEPS = ((0.77, "x-slow"), (0.92, "slow"), (1.1, None), (1.35, "fast"), (float("inf"), "x-fast"))
_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
_LATIN = re.compile(r"[A-Za-z]")
_LETTER = re.compile(r"[^\W\d_]")


@dataclass(frozen=True, slots=True)
class SileroModel:
    name: str
    url: str
    default_voice: str


MODELS = {
    "ru": SileroModel("v5_ru", "https://models.silero.ai/models/tts/ru/v5_ru.pt", "xenia"),
    "en": SileroModel("v3_en", "https://models.silero.ai/models/tts/en/v3_en.pt", "en_0"),
}

Fetcher = Callable[[str, RefreshCancellation | None], bytes]
ModelLoader = Callable[[Path], Any]
Normalizer = Callable[[str], str]
LLMTransliterate = Callable[[list[str]], Mapping[str, str]]


def _fetch(url: str, cancellation: RefreshCancellation | None) -> bytes:
    request = build_request(url, headers=newsr_headers())
    with open_request(request, cancellation, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return cancellable_read(response, cancellation)


def _load_package(path: Path) -> Any:
    from torch import package

    # Loading warnings on stderr would corrupt the terminal UI.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return package.PackageImporter(str(path)).load_pickle("tts_models", "model")


def check_dependencies() -> None:
    missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    if missing:
        raise TTSEngineError(f"{INSTALL_HINT} (missing: {', '.join(missing)})")


def speech_rate(speed: float) -> str | None:
    return next(rate for limit, rate in RATE_STEPS if speed < limit)


class SileroTTSEngine:
    name = "silero"
    max_chars = 1000

    def __init__(
        self,
        config: TTSSileroConfig,
        *,
        speed: float,
        llm_transliterate: LLMTransliterate | None = None,
        fetch: Fetcher = _fetch,
        model_loader: ModelLoader = _load_package,
        normalizers: Mapping[str, Normalizer] | None = None,
        dependency_check: Callable[[], None] = check_dependencies,
    ) -> None:
        self._config = config
        self._models_dir = Path(config.models_dir)
        self._rate = speech_rate(speed)
        self._llm_transliterate = llm_transliterate
        self._fetch = fetch
        self._model_loader = model_loader
        self._normalizers: dict[str, Normalizer] = dict(normalizers or {})
        self._dependency_check = dependency_check
        self._dependencies_checked = False
        self._models: dict[str, Any] = {}
        self._lock = Lock()

    def synthesize(
        self,
        text: str,
        language: str | None,
        cancellation: RefreshCancellation | None = None,
    ) -> SynthesizedAudio:
        configure_tts_logger()
        language = self.language_for(text, language)
        with self._lock:
            if not self._dependencies_checked:
                # Checked before any download, so a missing install does not fetch models first.
                self._dependency_check()
                self._dependencies_checked = True
            model = self._model(language, cancellation)
            voice = self.voice_for(language, model)
            prepared = self._normalizer(language)(text)
            LOGGER.info(
                "synthesis_start engine=silero voice=%s text_chars=%s prepared_chars=%s",
                voice,
                len(text),
                len(prepared),
            )
            samples = self._render(model, voice, prepared, cancellation)
        return SynthesizedAudio(data=_wav_bytes(samples), format="wav")

    @staticmethod
    def language_for(text: str, language: str | None) -> str:
        if language:
            language = language.lower()
            if language not in MODELS:
                raise TTSEngineError(f"silero voices speak Russian and English; no voice for '{language}'")
            return language
        return "ru" if len(_CYRILLIC.findall(text)) >= len(_LATIN.findall(text)) else "en"

    def voice_for(self, language: str, model: Any = None) -> str:
        voice = self._config.voices.get(language) or MODELS[language].default_voice
        speakers = getattr(model, "speakers", None)
        if speakers and voice not in speakers:
            available = ", ".join(speaker for speaker in speakers if speaker != "random")
            raise TTSEngineError(f"silero voice '{voice}' is not in model {MODELS[language].name}; available: {available}")
        return voice

    def _model(self, language: str, cancellation: RefreshCancellation | None) -> Any:
        loaded = self._models.get(language)
        if loaded is not None:
            return loaded
        spec = MODELS[language]
        path = self._models_dir / f"{spec.name}.pt"
        self._ensure_file(path, spec.url, cancellation)
        try:
            loaded = self._model_loader(path)
        except ImportError as exc:
            raise TTSEngineError(INSTALL_HINT) from exc
        except Exception as exc:
            raise TTSEngineError(f"silero could not load model {spec.name}: {exc}") from exc
        self._models[language] = loaded
        return loaded

    def _normalizer(self, language: str) -> Normalizer:
        normalizer = self._normalizers.get(language)
        if normalizer is not None:
            return normalizer
        try:
            from ...tts.normalize import RussianSpeechNormalizer, TermTransliterator, normalize_english
        except ImportError as exc:
            raise TTSEngineError(INSTALL_HINT) from exc
        if language == "ru":
            transliterator = TermTransliterator(self._models_dir, llm=self._llm_transliterate)
            normalizer = RussianSpeechNormalizer(transliterator, self._config.lexicon).normalize
        else:
            normalizer = normalize_english
        self._normalizers[language] = normalizer
        return normalizer

    def _render(self, model: Any, voice: str, text: str, cancellation: RefreshCancellation | None) -> list[Any]:
        import numpy as np

        pieces: list[Any] = []
        for paragraph in text.split("\n\n"):
            for chunk in split_chunks(paragraph, PIECE_CHARS):
                if not _LETTER.search(chunk):
                    continue
                if cancellation is not None:
                    cancellation.raise_if_cancelled()
                pieces.append(np.asarray(self._apply(model, voice, chunk), dtype=np.float32))
                pieces.append(np.zeros(int(SAMPLE_RATE * SENTENCE_PAUSE_SECONDS), dtype=np.float32))
            pieces.append(np.zeros(int(SAMPLE_RATE * PARAGRAPH_PAUSE_SECONDS), dtype=np.float32))
        if not any(len(piece) and piece.any() for piece in pieces):
            raise TTSEngineError("silero synthesis returned no audio")
        return pieces

    def _apply(self, model: Any, voice: str, text: str) -> Any:
        try:
            if self._rate is None:
                return model.apply_tts(text=text, speaker=voice, sample_rate=SAMPLE_RATE)
            ssml = f'<speak><prosody rate="{self._rate}">{escape(text)}</prosody></speak>'
            return model.apply_tts(ssml_text=ssml, speaker=voice, sample_rate=SAMPLE_RATE)
        except RefreshCancelled:
            raise
        except Exception as exc:
            LOGGER.error("synthesis_failed engine=silero voice=%s error_type=%s error=%s", voice, type(exc).__name__, exc)
            raise TTSEngineError(f"silero synthesis failed: {exc}") from exc

    def _ensure_file(self, path: Path, url: str, cancellation: RefreshCancellation | None) -> None:
        if path.exists() and path.stat().st_size > 0:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        LOGGER.info("download_start engine=silero url=%s", url)
        try:
            data = self._fetch(url, cancellation)
        except RefreshCancelled:
            raise
        except Exception as exc:
            LOGGER.error("download_failed engine=silero url=%s error_type=%s error=%s", url, type(exc).__name__, exc)
            raise TTSEngineError(f"silero download failed for {path.name}: {exc}") from exc
        partial_path = path.with_name(f"{path.name}.part")
        partial_path.write_bytes(data)
        partial_path.replace(path)
        LOGGER.info("download_done engine=silero path=%s bytes=%s", path, len(data))


def _wav_bytes(pieces: list[Any]) -> bytes:
    import numpy as np

    samples = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())
    return buffer.getvalue()
