from __future__ import annotations

from newsr.tts.normalize import RussianSpeechNormalizer


def make_normalizer(lexicon: dict[str, str] | None = None) -> RussianSpeechNormalizer:
    return RussianSpeechNormalizer(lambda terms: {term: f"<{term}>" for term in terms}, lexicon)


def test_normalizer_rewrites_names_numbers_and_dates() -> None:
    text = make_normalizer().normalize("Etched привлекла $700 млн, а Nvidia выпустила чип 28 сентября 2026 г.")

    assert text == (
        "<Etched> привлекла семьсот миллионов долларов, а энв+идиа выпустила чип "
        "двадцать восьмого сентября две тысячи двадцать шестого года"
    )


def test_normalizer_spells_cyrillic_acronyms_and_expands_abbreviations() -> None:
    text = make_normalizer().normalize("США, ИИ, ФРС и НАТО обсудили ВВП (т. е. рост на 2,5%).")

    assert text == "сэ-шэ-+а, и-+и, эф-эр-+эс и нато обсудили вэ-вэ-п+э то есть рост на две целых пять десятых процента."


def test_user_lexicon_overrides_latin_and_cyrillic_words() -> None:
    normalizer = make_normalizer({"Nvidia": "нв+идиа", "Etched": "+этчед", "замок": "з+амок"})

    assert normalizer.normalize("Старый замок, Nvidia и Etched.") == "Старый з+амок, нв+идиа и +этчед."


def test_normalizer_drops_brackets_and_quotes() -> None:
    assert make_normalizer().normalize("Галерея [фото] «новинки»") == "Галерея фото новинки"
