from __future__ import annotations

import io
import json
import wave
from dataclasses import dataclass
from pathlib import Path

import pytest

from newsr.config import TTSPiperConfig
from newsr.providers.tts.base import TTSEngineError
from newsr.providers.tts.piper import PIPER_VOICES_URL, PiperTTSEngine, voice_file_url

VOICES_INDEX = {
    "ru_RU-irina-medium": {"language": {"family": "ru", "code": "ru_RU"}, "quality": "medium"},
    "ru_RU-denis-low": {"language": {"family": "ru", "code": "ru_RU"}, "quality": "low"},
    "de_DE-thorsten-high": {"language": {"family": "de", "code": "de_DE"}, "quality": "high"},
    "en_GB-alan-medium": {"language": {"family": "en", "code": "en_GB"}, "quality": "medium"},
    "en_US-amy-low": {"language": {"family": "en", "code": "en_US"}, "quality": "low"},
    "en_US-ryan-medium": {"language": {"family": "en", "code": "en_US"}, "quality": "medium"},
}


@dataclass
class FakeChunk:
    audio_int16_bytes: bytes
    sample_rate: int = 22050
    sample_width: int = 2
    sample_channels: int = 1


class FakeVoice:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.calls: list[tuple[str, object]] = []

    def synthesize(self, text: str, syn_config=None):  # type: ignore[no-untyped-def]
        self.calls.append((text, syn_config))
        yield FakeChunk(b"\x01\x00" * 4)
        yield FakeChunk(b"\x02\x00" * 4)


class FakeFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str, cancellation=None) -> bytes:  # type: ignore[no-untyped-def]
        self.urls.append(url)
        if "voices.json" in url:
            return json.dumps(VOICES_INDEX).encode("utf-8")
        return b"model-bytes"


def make_engine(tmp_path: Path, voices: dict[str, str] | None = None, *, speed: float = 1.0):
    fetcher = FakeFetcher()
    loaded: list[FakeVoice] = []

    def load(path: Path) -> FakeVoice:
        voice = FakeVoice(path)
        loaded.append(voice)
        return voice

    engine = PiperTTSEngine(
        TTSPiperConfig(models_dir=str(tmp_path / "piper"), voices=voices or {}),
        speed=speed,
        fetch=fetcher,
        voice_loader=load,
        synthesis_config=lambda length_scale: {"length_scale": length_scale},
    )
    return engine, fetcher, loaded


def test_voice_file_url_follows_piper_voice_layout() -> None:
    assert voice_file_url("ru_RU-irina-medium", ".onnx") == (
        f"{PIPER_VOICES_URL}/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx?download=true"
    )
    with pytest.raises(TTSEngineError):
        voice_file_url("irina", ".onnx")


def test_piper_engine_downloads_voice_once_and_writes_wav(tmp_path: Path) -> None:
    engine, fetcher, loaded = make_engine(tmp_path, {"en": "en_US-lessac-medium"}, speed=2.0)

    audio = engine.synthesize("Hello", "en")
    engine.synthesize("Again", "en")

    assert audio.format == "wav"
    with wave.open(io.BytesIO(audio.data)) as wav_file:
        assert wav_file.getframerate() == 22050
        assert wav_file.getnchannels() == 1
        assert wav_file.getnframes() == 8
    assert fetcher.urls == [
        voice_file_url("en_US-lessac-medium", ".onnx"),
        voice_file_url("en_US-lessac-medium", ".onnx.json"),
    ]
    assert (tmp_path / "piper" / "en_US-lessac-medium.onnx").read_bytes() == b"model-bytes"
    assert len(loaded) == 1
    assert loaded[0].calls == [("Hello", {"length_scale": 0.5}), ("Again", {"length_scale": 0.5})]


def test_piper_engine_reuses_existing_model_files(tmp_path: Path) -> None:
    models_dir = tmp_path / "piper"
    models_dir.mkdir()
    (models_dir / "en_US-lessac-medium.onnx").write_bytes(b"model")
    (models_dir / "en_US-lessac-medium.onnx.json").write_text("{}", encoding="utf-8")
    engine, fetcher, _loaded = make_engine(tmp_path, {"default": "en_US-lessac-medium"})

    engine.synthesize("Hello", None)

    assert fetcher.urls == []


def test_piper_engine_discovers_medium_voice_for_language(tmp_path: Path) -> None:
    engine, _fetcher, _loaded = make_engine(tmp_path)

    assert engine.voice_for("ru") == "ru_RU-irina-medium"
    assert engine.voice_for("de") == "de_DE-thorsten-high"
    assert engine.voice_for("en") == "en_US-ryan-medium"
    assert engine.voice_for("ja") == "en_US-lessac-medium"
