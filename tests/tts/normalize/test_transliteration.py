from __future__ import annotations

import json
from pathlib import Path
from threading import Event, Thread

import pytest

from newsr.cancellation import RefreshCancellation, RefreshCancelled
from newsr.tts.normalize.transliteration import CACHE_FILE_NAME, LLM_BATCH_TERMS, TermTransliterator, looks_spelled

RUNORM_ANSWERS = {
    "Etched": "этчед",
    "Jane Street": "джейн стрит",
    "Elon Musk": "элон эм йю эс кей",
    "Elon": "элон",
    "Musk": "эм йю эс кей",
    "Ultra": "йю ти эр эй",
    "Galaxy Ultra": "гэлакси йю ти эр эй",
    "Galaxy": "гэлакси",
}


class FakeRunorm:
    def __init__(self) -> None:
        self.loads: list[Path] = []
        self.calls: list[str] = []

    def load(self, cache_dir: Path):  # type: ignore[no-untyped-def]
        self.loads.append(cache_dir)

        def kirillize(text: str) -> str:
            self.calls.append(text)
            return RUNORM_ANSWERS.get(text, text)

        return kirillize


class FakeLLM:
    def __init__(self, answers: dict[str, str] | None = None, error: Exception | None = None) -> None:
        self.answers = answers or {}
        self.error = error
        self.calls: list[list[str]] = []
        self.cancellations: list[RefreshCancellation | None] = []

    def __call__(self, terms: list[str], cancellation: RefreshCancellation | None = None) -> dict[str, str]:
        self.calls.append(list(terms))
        self.cancellations.append(cancellation)
        if self.error is not None:
            raise self.error
        return {term: self.answers[term] for term in terms if term in self.answers}


class BlockingLLM(FakeLLM):
    def __init__(self, answers: dict[str, str]) -> None:
        super().__init__(answers)
        self.started = Event()
        self.release = Event()

    def __call__(self, terms: list[str], cancellation: RefreshCancellation | None = None) -> dict[str, str]:
        self.started.set()
        assert self.release.wait(5)
        return super().__call__(terms, cancellation)


@pytest.mark.parametrize(
    ("output", "spelled"),
    [
        ("этчед", False),
        ("джейн стрит", False),
        ("эм йю эс кей", True),
        ("ти-эс-эм-си", True),
        ("Musk", True),
        ("", True),
        ("айфон и айпэд", False),
    ],
)
def test_looks_spelled_detects_letter_by_letter_output(output: str, spelled: bool) -> None:
    assert looks_spelled(output) is spelled


def test_transliterator_uses_runorm_and_reuses_cache_file(tmp_path: Path) -> None:
    runorm = FakeRunorm()
    transliterator = TermTransliterator(tmp_path, runorm_loader=runorm.load)

    assert transliterator(["Etched", "Jane Street"]) == {"Etched": "этчед", "Jane Street": "джейн стрит"}
    assert runorm.loads == [tmp_path / "runorm"]
    assert json.loads((tmp_path / CACHE_FILE_NAME).read_text(encoding="utf-8")) == {
        "Etched": "этчед",
        "Jane Street": "джейн стрит",
    }

    restarted = TermTransliterator(tmp_path, runorm_loader=runorm.load)
    assert restarted(["Etched"]) == {"Etched": "этчед"}
    assert runorm.calls == ["Etched", "Jane Street"]


def test_transliterator_retries_spelled_runs_word_by_word(tmp_path: Path) -> None:
    runorm = FakeRunorm()
    RUNORM_ANSWERS["Galaxy Ultra"] = "гэлакси йю ти эр эй"
    llm = FakeLLM({"Elon Musk": "илон маск", "Galaxy Ultra": "гэлакси ультра"})
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=runorm.load)

    result = transliterator.prepare(["Elon Musk", "Galaxy Ultra"])

    assert result == {"Elon Musk": "илон маск", "Galaxy Ultra": "гэлакси ультра"}
    assert runorm.calls == ["Elon Musk", "Elon", "Musk", "Galaxy Ultra", "Galaxy", "Ultra"]
    assert llm.calls == [["Elon Musk", "Galaxy Ultra"]]


def test_transliterator_rejects_spelled_llm_answers_and_does_not_retry_them(tmp_path: Path) -> None:
    llm = FakeLLM({"Ultra": "ю ти ар эй"})
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=FakeRunorm().load)

    assert transliterator.prepare(["Ultra"]) == {}
    assert transliterator.prepare(["Ultra"]) == {}
    assert llm.calls == [["Ultra"]]
    assert not (tmp_path / CACHE_FILE_NAME).exists()


def test_transliterator_falls_back_to_llm_when_runorm_cannot_load(tmp_path: Path) -> None:
    loads: list[Path] = []

    def broken_loader(cache_dir: Path):  # type: ignore[no-untyped-def]
        loads.append(cache_dir)
        raise OSError("no network")

    llm = FakeLLM({"Etched": "этчед", "Toshiba": "тошиба"})
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=broken_loader)

    assert transliterator.prepare(["Etched"]) == {"Etched": "этчед"}
    assert transliterator.prepare(["Toshiba"]) == {"Toshiba": "тошиба"}
    assert len(loads) == 1


def test_transliterator_survives_llm_errors(tmp_path: Path) -> None:
    llm = FakeLLM(error=RuntimeError("LLM down"))
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=FakeRunorm().load)

    assert transliterator.prepare(["Ultra", "Etched"]) == {"Etched": "этчед"}
    assert transliterator.prepare(["Ultra"]) == {}
    assert llm.calls == [["Ultra"], ["Ultra"]]


def test_transliterator_call_never_asks_the_llm(tmp_path: Path) -> None:
    llm = FakeLLM({"Ultra": "ультра"})
    runorm = FakeRunorm()
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=runorm.load)

    assert transliterator(["Ultra", "Etched"]) == {"Etched": "этчед"}
    assert transliterator(["Ultra"]) == {}
    assert llm.calls == []
    assert runorm.calls == ["Ultra", "Etched"]


def test_transliterator_prepare_asks_the_llm_for_terms_spelled_during_synthesis(tmp_path: Path) -> None:
    llm = FakeLLM({"Ultra": "ультра"})
    runorm = FakeRunorm()
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=runorm.load)
    cancellation = RefreshCancellation()

    assert transliterator(["Ultra"]) == {}
    assert transliterator.prepare(["Ultra"], cancellation) == {"Ultra": "ультра"}
    assert transliterator(["Ultra"]) == {"Ultra": "ультра"}
    assert runorm.calls == ["Ultra"]
    assert llm.calls == [["Ultra"]]
    assert llm.cancellations == [cancellation]


def test_transliterator_prepare_reraises_cancellation_and_marks_nothing(tmp_path: Path) -> None:
    llm = FakeLLM(error=RefreshCancelled("stopped"))
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=FakeRunorm().load)

    with pytest.raises(RefreshCancelled):
        transliterator.prepare(["Ultra"])

    llm.error = None
    llm.answers = {"Ultra": "ультра"}
    assert transliterator.prepare(["Ultra"]) == {"Ultra": "ультра"}


def test_transliterator_prepare_splits_llm_requests_into_batches(tmp_path: Path) -> None:
    terms = [f"Term{index}" for index in range(LLM_BATCH_TERMS + 5)]
    llm = FakeLLM({term: "терм" for term in terms})
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=lambda _path: lambda _text: "")

    assert len(transliterator.prepare(terms)) == len(terms)
    assert [len(batch) for batch in llm.calls] == [LLM_BATCH_TERMS, 5]


def test_transliterator_call_does_not_wait_for_a_running_llm_request(tmp_path: Path) -> None:
    (tmp_path / CACHE_FILE_NAME).write_text(json.dumps({"Etched": "этчед"}), encoding="utf-8")
    llm = BlockingLLM({"Ultra": "ультра"})
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=FakeRunorm().load)
    preparation = Thread(target=transliterator.prepare, args=(["Ultra"],))
    preparation.start()
    try:
        assert llm.started.wait(5)
        assert transliterator(["Etched"]) == {"Etched": "этчед"}
    finally:
        llm.release.set()
        preparation.join(5)
    assert transliterator(["Ultra"]) == {"Ultra": "ультра"}
