from __future__ import annotations

from pathlib import Path
from threading import Event, Thread

import numpy as np

from newsr.cancellation import RefreshCancellation
from newsr.config import TTSSileroConfig
from newsr.providers.tts.base import TTSEngineError
from newsr.providers.tts.silero import SileroTTSEngine
from newsr.tts.normalize import TermTransliterator


class FakeModel:
    speakers = ["xenia", "en_0"]

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def apply_tts(self, **kwargs: object) -> np.ndarray:
        self.calls.append(kwargs)
        return np.full(100, 0.5, dtype=np.float32)


class FakeLLM:
    def __init__(self, answers: dict[str, str]) -> None:
        self.answers = answers
        self.calls: list[list[str]] = []
        self.started = Event()
        self.release: Event | None = None

    def __call__(self, terms: list[str], cancellation: RefreshCancellation | None = None) -> dict[str, str]:
        self.calls.append(list(terms))
        self.started.set()
        if self.release is not None:
            assert self.release.wait(5)
        return {term: self.answers[term] for term in terms if term in self.answers}


class RecordingTransliterator:
    def __init__(self) -> None:
        self.prepared: list[tuple[list[str], RefreshCancellation | None]] = []

    def __call__(self, terms: list[str]) -> dict[str, str]:
        return {}

    def prepare(self, terms: list[str], cancellation: RefreshCancellation | None = None) -> dict[str, str]:
        self.prepared.append((list(terms), cancellation))
        return {}


def spelling_runorm(_path: Path):  # type: ignore[no-untyped-def]
    return lambda _text: "эй би си"


def make_engine(tmp_path: Path, *, llm: FakeLLM | None = None, transliterator_factory=None, dependency_check=None):  # type: ignore[no-untyped-def]
    model = FakeModel()
    factory = transliterator_factory or (
        lambda models_dir, llm_transliterate: TermTransliterator(
            models_dir,
            llm=llm_transliterate,
            runorm_loader=spelling_runorm,
        )
    )
    engine = SileroTTSEngine(
        TTSSileroConfig(models_dir=str(tmp_path / "silero")),
        speed=1.0,
        llm_transliterate=llm,
        fetch=lambda _url, _cancellation: b"model",
        model_loader=lambda _path: model,
        dependency_check=dependency_check or (lambda: None),
        transliterator_factory=factory,
    )
    return engine, model


def test_silero_prepare_sends_russian_terms_in_one_batch(tmp_path: Path) -> None:
    transliterator = RecordingTransliterator()
    engine, model = make_engine(tmp_path, transliterator_factory=lambda _dir, _llm: transliterator)
    cancellation = RefreshCancellation()

    engine.prepare(
        [
            ("Etched выпустила чип.", "ru"),
            ("Nvidia и Etched снова спорят.", "ru"),
            ("Elon Musk spoke.", "en"),
            ("Bonjour Paris.", "fr"),
            ("Компания Cerebras ответила.", None),
        ],
        cancellation,
    )

    assert transliterator.prepared == [(["Etched", "Cerebras"], cancellation)]
    assert model.calls == []


def test_silero_prepare_lets_synthesis_skip_the_llm(tmp_path: Path) -> None:
    llm = FakeLLM({"Etched": "этчед"})
    engine, model = make_engine(tmp_path, llm=llm)

    engine.prepare([("Etched выпустила чип.", "ru")])
    engine.synthesize("Etched выпустила чип.", "ru")

    assert llm.calls == [["Etched"]]
    assert model.calls[0]["text"] == "этчед выпустила чип."


def test_silero_synthesis_never_asks_the_llm(tmp_path: Path) -> None:
    llm = FakeLLM({"Cerebras": "церебрас"})
    engine, model = make_engine(tmp_path, llm=llm)

    engine.synthesize("Cerebras выпустила чип.", "ru")

    assert llm.calls == []
    assert "церебрас" not in str(model.calls[0]["text"])


def test_silero_prepare_skips_work_when_dependencies_are_missing(tmp_path: Path) -> None:
    checks: list[int] = []
    factories: list[Path] = []

    def missing() -> None:
        checks.append(1)
        raise TTSEngineError("missing torch")

    def factory(models_dir: Path, _llm):  # type: ignore[no-untyped-def]
        factories.append(models_dir)
        return RecordingTransliterator()

    engine, _model = make_engine(tmp_path, transliterator_factory=factory, dependency_check=missing)

    engine.prepare([("Etched выпустила чип.", "ru")])
    engine.prepare([("Etched выпустила чип.", "ru")])

    assert checks == [1]
    assert factories == []


def test_silero_synthesis_runs_while_preparation_waits_for_the_llm(tmp_path: Path) -> None:
    llm = FakeLLM({"Etched": "этчед", "Cerebras": "церебрас"})
    engine, model = make_engine(tmp_path, llm=llm)
    engine.prepare([("Etched выпустила чип.", "ru")])
    llm.started.clear()
    llm.release = Event()
    preparation = Thread(target=engine.prepare, args=([("Cerebras ответила.", "ru")],))
    preparation.start()
    try:
        assert llm.started.wait(5)
        engine.synthesize("Etched выпустила чип.", "ru")
        assert model.calls[-1]["text"] == "этчед выпустила чип."
    finally:
        llm.release.set()
        preparation.join(5)
    assert llm.calls == [["Etched"], ["Cerebras"]]
