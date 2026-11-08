from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ...cancellation import RefreshCancellation
from ...runtime_logging import configure_cache_logger

LOGGER = logging.getLogger("newsr.tts")
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


def configure_tts_logger() -> None:
    configure_cache_logger(LOGGER, filename="newsr-tts.log")


class TTSEngineError(RuntimeError):
    """Raised when a TTS engine cannot synthesize speech."""


@dataclass(frozen=True, slots=True)
class SynthesizedAudio:
    data: bytes
    format: str


class TransliterationLLM(Protocol):
    def transliterate_terms(
        self,
        terms: list[str],
        cancellation: RefreshCancellation | None = None,
    ) -> dict[str, str]:
        ...


class TTSEngine(Protocol):
    name: str
    max_chars: int

    def synthesize(
        self,
        text: str,
        language: str | None,
        cancellation: RefreshCancellation | None = None,
    ) -> SynthesizedAudio:
        ...


@runtime_checkable
class PreparingTTSEngine(TTSEngine, Protocol):
    """An engine that does its slow text preparation, such as LLM requests, before playback."""

    def prepare(
        self,
        texts: Sequence[tuple[str, str | None]],
        cancellation: RefreshCancellation | None = None,
    ) -> None:
        """Prepare `(text, language)` pairs so that synthesizing them later needs no LLM request."""
