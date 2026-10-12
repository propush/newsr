from __future__ import annotations

import json
from pathlib import Path

import pytest

from newsr.tts.normalize.transliteration import CACHE_FILE_NAME, TermTransliterator, looks_spelled

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

    def __call__(self, terms: list[str]) -> dict[str, str]:
        self.calls.append(list(terms))
        if self.error is not None:
            raise self.error
        return {term: self.answers[term] for term in terms if term in self.answers}


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

    result = transliterator(["Elon Musk", "Galaxy Ultra"])

    assert result == {"Elon Musk": "илон маск", "Galaxy Ultra": "гэлакси ультра"}
    assert runorm.calls == ["Elon Musk", "Elon", "Musk", "Galaxy Ultra", "Galaxy", "Ultra"]
    assert llm.calls == [["Elon Musk", "Galaxy Ultra"]]


def test_transliterator_rejects_spelled_llm_answers_and_does_not_retry_them(tmp_path: Path) -> None:
    llm = FakeLLM({"Ultra": "ю ти ар эй"})
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=FakeRunorm().load)

    assert transliterator(["Ultra"]) == {}
    assert transliterator(["Ultra"]) == {}
    assert llm.calls == [["Ultra"]]
    assert not (tmp_path / CACHE_FILE_NAME).exists()


def test_transliterator_falls_back_to_llm_when_runorm_cannot_load(tmp_path: Path) -> None:
    loads: list[Path] = []

    def broken_loader(cache_dir: Path):  # type: ignore[no-untyped-def]
        loads.append(cache_dir)
        raise OSError("no network")

    llm = FakeLLM({"Etched": "этчед", "Toshiba": "тошиба"})
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=broken_loader)

    assert transliterator(["Etched"]) == {"Etched": "этчед"}
    assert transliterator(["Toshiba"]) == {"Toshiba": "тошиба"}
    assert len(loads) == 1


def test_transliterator_survives_llm_errors(tmp_path: Path) -> None:
    llm = FakeLLM(error=RuntimeError("LLM down"))
    transliterator = TermTransliterator(tmp_path, llm=llm, runorm_loader=FakeRunorm().load)

    assert transliterator(["Ultra", "Etched"]) == {"Etched": "этчед"}
