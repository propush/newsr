from __future__ import annotations

from newsr.tts.normalize.latin import LatinRewriter, classify, spell_latin

PRONUNCIATIONS = {"Android": "андр+оид", "Beta": "б+ета", "Mac mini": "мак м+ини", "Mac": "м+ак", "Wi-Fi": "в+ай-ф+ай"}


class RecordingTransliterator:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, terms: list[str]) -> dict[str, str]:
        self.calls.append(terms)
        return {term: f"<{term}>" for term in terms if term != "Unknown"}


def rewrite(text: str) -> tuple[str, RecordingTransliterator]:
    transliterator = RecordingTransliterator()
    return LatinRewriter(PRONUNCIATIONS, transliterator).rewrite(text), transliterator


def test_spell_latin_stresses_last_letter_and_keeps_plural() -> None:
    assert spell_latin("TSMC") == "ти-эс-эм-с+и"
    assert spell_latin("GPUs") == "джи-пи-ю-+эс"
    assert spell_latin("a") == "+эй"


def test_classify_splits_versions_hyphens_and_mixed_tokens() -> None:
    assert classify("Pixel 10a Pro") == [("word", "Pixel"), ("number", "10"), ("acronym", "a"), ("word", "Pro")]
    assert classify("USB-C") == [("acronym", "USB"), ("acronym", "C")]
    assert classify("Beta 6.1") == [("word", "Beta"), ("number", "6.1")]


def test_rewriter_reads_versions_acronyms_and_pronunciations_inside_spans() -> None:
    text, transliterator = rewrite("Скриншоты Android 17 QPR2 Beta 6.1 показаны слева.")

    assert text == "Скриншоты андр+оид семнадцать кью-пи-+ар два б+ета шесть точка один показаны слева."
    assert transliterator.calls == []


def test_rewriter_keeps_sentence_breaks_and_hyphenated_russian_suffixes() -> None:
    text, transliterator = rewrite("Для настольных Mac. Mac mini и nearline-накопителей с Wi-Fi 7.")

    assert text == "Для настольных м+ак. мак м+ини и <nearline>-накопителей с в+ай-ф+ай семь."
    assert transliterator.calls == [["nearline"]]


def test_rewriter_transliterates_word_runs_once_and_spells_unknown_words() -> None:
    text, transliterator = rewrite("Фирма Jane Street и Unknown, снова Jane Street.")

    assert text == "Фирма <Jane Street> и ю-эн-кей-эн-оу-дабл-ю-+эн, снова <Jane Street>."
    assert transliterator.calls == [["Jane Street", "Unknown"]]


def test_rewriter_drops_articles_and_leaves_numbers_before_months_and_units() -> None:
    text, _transliterator = rewrite("По данным The Information, Blackwell Ultra 28 сентября и Pixel 9 16 ГБ.")

    assert text == "По данным <Information>, <Blackwell Ultra> 28 сентября и <Pixel> девять 16 ГБ."
