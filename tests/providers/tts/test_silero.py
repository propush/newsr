from __future__ import annotations

import io
import wave
from pathlib import Path

import numpy as np
import pytest

from newsr.cancellation import RefreshCancellation, RefreshCancelled
from newsr.config import TTSSileroConfig
from newsr.providers.tts.base import TTSEngineError
from newsr.providers.tts.silero import (
    INSTALL_HINT,
    MODELS,
    check_dependencies,
    PARAGRAPH_PAUSE_SECONDS,
    SAMPLE_RATE,
    SENTENCE_PAUSE_SECONDS,
    SileroTTSEngine,
    speech_rate,
)

SPEECH_SAMPLES = 100


class FakeModel:
    def __init__(self, path: Path, speakers: list[str]) -> None:
        self.path = path
        self.speakers = speakers
        self.calls: list[dict[str, object]] = []

    def apply_tts(self, **kwargs: object) -> np.ndarray:
        self.calls.append(kwargs)
        return np.full(SPEECH_SAMPLES, 0.5, dtype=np.float32)


class FakeFetcher:
    def __init__(self, error: Exception | None = None) -> None:
        self.urls: list[str] = []
        self.error = error

    def __call__(self, url: str, cancellation=None) -> bytes:  # type: ignore[no-untyped-def]
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        return b"model-bytes"


def make_engine(
    tmp_path: Path,
    voices: dict[str, str] | None = None,
    *,
    speed: float = 1.0,
    fetcher: FakeFetcher | None = None,
    loader=None,  # type: ignore[no-untyped-def]
    dependency_check=lambda: None,  # type: ignore[no-untyped-def]
):
    fetcher = fetcher or FakeFetcher()
    loaded: list[FakeModel] = []

    def load(path: Path) -> FakeModel:
        speakers = ["en_0", "en_12", "random"] if "en" in path.name else ["xenia", "baya", "aidar"]
        model = FakeModel(path, speakers)
        loaded.append(model)
        return model

    engine = SileroTTSEngine(
        TTSSileroConfig(models_dir=str(tmp_path / "silero"), voices=voices or {}),
        speed=speed,
        fetch=fetcher,
        model_loader=loader or load,
        normalizers={"ru": lambda text: f"ru:{text}", "en": lambda text: f"en:{text}"},
        dependency_check=dependency_check,
    )
    return engine, fetcher, loaded


def wav_frames(data: bytes) -> tuple[int, int, int]:
    with wave.open(io.BytesIO(data)) as wav_file:
        return wav_file.getframerate(), wav_file.getnchannels(), wav_file.getnframes()


def test_silero_engine_downloads_model_once_and_writes_wav(tmp_path: Path) -> None:
    engine, fetcher, loaded = make_engine(tmp_path)

    audio = engine.synthesize("Привет.", "ru")
    engine.synthesize("Ещё раз.", "ru")

    assert audio.format == "wav"
    rate, channels, frames = wav_frames(audio.data)
    assert (rate, channels) == (SAMPLE_RATE, 1)
    pauses = int(SAMPLE_RATE * SENTENCE_PAUSE_SECONDS) + int(SAMPLE_RATE * PARAGRAPH_PAUSE_SECONDS)
    assert frames == SPEECH_SAMPLES + pauses
    assert fetcher.urls == [MODELS["ru"].url]
    assert (tmp_path / "silero" / "v5_ru.pt").read_bytes() == b"model-bytes"
    assert len(loaded) == 1
    assert loaded[0].calls == [
        {"text": "ru:Привет.", "speaker": "xenia", "sample_rate": SAMPLE_RATE},
        {"text": "ru:Ещё раз.", "speaker": "xenia", "sample_rate": SAMPLE_RATE},
    ]


def test_silero_engine_reuses_existing_model_file(tmp_path: Path) -> None:
    models_dir = tmp_path / "silero"
    models_dir.mkdir()
    (models_dir / "v3_en.pt").write_bytes(b"model")
    engine, fetcher, loaded = make_engine(tmp_path)

    engine.synthesize("Hello.", "en")

    assert fetcher.urls == []
    assert loaded[0].calls[0]["speaker"] == "en_0"
    assert loaded[0].calls[0]["text"] == "en:Hello."


def test_silero_engine_uses_configured_voices_per_language(tmp_path: Path) -> None:
    engine, _fetcher, loaded = make_engine(tmp_path, {"ru": "baya", "en": "en_12"})

    engine.synthesize("Привет.", "RU")
    engine.synthesize("Hello.", "en")

    assert [model.calls[0]["speaker"] for model in loaded] == ["baya", "en_12"]


def test_silero_engine_rejects_unknown_voice_with_available_list(tmp_path: Path) -> None:
    engine, _fetcher, _loaded = make_engine(tmp_path, {"en": "en_999"})

    with pytest.raises(TTSEngineError, match="available: en_0, en_12$"):
        engine.synthesize("Hello.", "en")


def test_silero_engine_detects_language_from_script_and_rejects_other_languages(tmp_path: Path) -> None:
    assert SileroTTSEngine.language_for("Компания Nvidia выпустила чип", None) == "ru"
    assert SileroTTSEngine.language_for("Nvidia released a chip", None) == "en"
    with pytest.raises(TTSEngineError, match="no voice for 'de'"):
        SileroTTSEngine.language_for("Hallo", "de")


@pytest.mark.parametrize(
    ("speed", "rate"),
    [(0.5, "x-slow"), (0.85, "slow"), (1.0, None), (1.05, None), (1.25, "fast"), (1.5, "x-fast"), (2.0, "x-fast")],
)
def test_speech_rate_rounds_speed_to_silero_steps(speed: float, rate: str | None) -> None:
    assert speech_rate(speed) == rate


def test_silero_engine_applies_speed_through_escaped_ssml(tmp_path: Path) -> None:
    engine, _fetcher, loaded = make_engine(tmp_path, speed=1.3)

    engine.synthesize("A & B <ok>.", "en")

    assert loaded[0].calls == [
        {
            "ssml_text": '<speak><prosody rate="fast">en:A &amp; B &lt;ok&gt;.</prosody></speak>',
            "speaker": "en_0",
            "sample_rate": SAMPLE_RATE,
        }
    ]


def test_silero_engine_synthesizes_paragraphs_separately_and_skips_empty_pieces(tmp_path: Path) -> None:
    engine, _fetcher, loaded = make_engine(tmp_path)

    audio = engine.synthesize("Первый абзац.\n\n...\n\nВторой абзац.", "ru")

    texts = [call["text"] for call in loaded[0].calls]
    assert texts == ["ru:Первый абзац.", "Второй абзац."]
    _rate, _channels, frames = wav_frames(audio.data)
    sentence_pause = int(SAMPLE_RATE * SENTENCE_PAUSE_SECONDS)
    paragraph_pause = int(SAMPLE_RATE * PARAGRAPH_PAUSE_SECONDS)
    assert frames == 2 * (SPEECH_SAMPLES + sentence_pause) + 3 * paragraph_pause


def test_silero_engine_stops_when_cancelled(tmp_path: Path) -> None:
    engine, _fetcher, loaded = make_engine(tmp_path)
    cancellation = RefreshCancellation()
    cancellation.cancel()

    with pytest.raises(RefreshCancelled):
        engine.synthesize("Привет.", "ru", cancellation)

    assert loaded[0].calls == []


def test_silero_engine_reports_missing_packages_before_downloading(tmp_path: Path) -> None:
    def missing_packages() -> None:
        raise TTSEngineError(INSTALL_HINT)

    engine, fetcher, loaded = make_engine(tmp_path, dependency_check=missing_packages)

    with pytest.raises(TTSEngineError, match=r'pip install -e "\.\[silero\]"'):
        engine.synthesize("Привет.", "ru")
    assert fetcher.urls == []
    assert loaded == []


def test_check_dependencies_names_missing_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util

    real_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: None if name in {"torch", "pymorphy3"} else real_find_spec(name),
    )

    with pytest.raises(TTSEngineError, match="missing: torch, pymorphy3"):
        check_dependencies()


def test_silero_engine_reports_import_errors_while_loading_model(tmp_path: Path) -> None:
    def missing_torch(path: Path) -> FakeModel:
        raise ImportError("No module named 'torch'")

    engine, _fetcher, _loaded = make_engine(tmp_path, loader=missing_torch)

    with pytest.raises(TTSEngineError, match="pip install"):
        engine.synthesize("Привет.", "ru")


def test_silero_engine_reports_download_failure(tmp_path: Path) -> None:
    engine, _fetcher, _loaded = make_engine(tmp_path, fetcher=FakeFetcher(OSError("offline")))

    with pytest.raises(TTSEngineError, match="silero download failed for v5_ru.pt: offline"):
        engine.synthesize("Привет.", "ru")
    assert not (tmp_path / "silero" / "v5_ru.pt").exists()


def test_silero_engine_wraps_synthesis_errors(tmp_path: Path) -> None:
    class BrokenModel(FakeModel):
        def apply_tts(self, **kwargs: object) -> np.ndarray:
            raise ValueError("bad symbol")

    engine, _fetcher, _loaded = make_engine(tmp_path, loader=lambda path: BrokenModel(path, ["xenia"]))

    with pytest.raises(TTSEngineError, match="silero synthesis failed: bad symbol"):
        engine.synthesize("Привет.", "ru")
