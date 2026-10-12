"""Russian text for Cyrillic-only voices: English names, acronyms, numbers, and units as Cyrillic words."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .latin import LatinRewriter, Transliterate, stress_last
from .pronunciations import CYRILLIC_PRONUNCIATIONS, CYRILLIC_WORD_ACRONYMS, LATIN_PRONUNCIATIONS
from .russian_numbers import russian_numbers_to_words

RUSSIAN_LETTER_NAMES = {
    "а": "а", "б": "бэ", "в": "вэ", "г": "гэ", "д": "дэ", "е": "е", "ё": "ё", "ж": "жэ", "з": "зэ", "и": "и",
    "й": "й", "к": "ка", "л": "эль", "м": "эм", "н": "эн", "о": "о", "п": "пэ", "р": "эр", "с": "эс", "т": "тэ",
    "у": "у", "ф": "эф", "х": "ха", "ц": "цэ", "ч": "че", "ш": "ша", "щ": "ща", "ъ": "", "ы": "ы", "ь": "", "э": "э",
    "ю": "ю", "я": "я",
}
RUSSIAN_ABBREVIATIONS = {
    "и т. д.": "и так далее",
    "и т.д.": "и так далее",
    "и т. п.": "и тому подобное",
    "и т.п.": "и тому подобное",
    "т. е.": "то есть",
    "т.е.": "то есть",
    "т. к.": "так как",
    "т.к.": "так как",
    "т. н.": "так называемый",
}

_LATIN = re.compile(r"[A-Za-z]")
_DROPPED = re.compile(r"[\[\]«»“”„\"()*_`]")
_CYRILLIC_ACRONYM = re.compile(r"(?<![А-ЯЁа-яё+])[А-ЯЁ]{2,6}(?![А-ЯЁа-яё])")


def _spell_cyrillic(match: re.Match[str]) -> str:
    word = match.group(0)
    if word in CYRILLIC_WORD_ACRONYMS:
        return word.lower()
    return stress_last([name for name in (RUSSIAN_LETTER_NAMES[char] for char in word.lower()) if name])


class RussianSpeechNormalizer:
    def __init__(self, transliterate: Transliterate, lexicon: Mapping[str, str] | None = None) -> None:
        latin = dict(LATIN_PRONUNCIATIONS)
        cyrillic = dict(CYRILLIC_PRONUNCIATIONS)
        for term, spoken in (lexicon or {}).items():
            (latin if _LATIN.search(term) else cyrillic)[term] = spoken
        self._latin = LatinRewriter(latin, transliterate)
        self._cyrillic = [
            (
                re.compile(
                    rf"(?<![А-Яа-яЁё+]){re.escape(term)}(?![А-Яа-яЁё])",
                    0 if term.isupper() else re.IGNORECASE,
                ),
                spoken,
            )
            for term, spoken in sorted(cyrillic.items(), key=lambda item: len(item[0]), reverse=True)
        ]

    def normalize(self, text: str) -> str:
        text = _DROPPED.sub("", text)
        for short, full in RUSSIAN_ABBREVIATIONS.items():
            text = text.replace(short, full)
        for pattern, spoken in self._cyrillic:
            text = pattern.sub(spoken, text)
        text = self._latin.rewrite(text)
        text = russian_numbers_to_words(text)
        text = _CYRILLIC_ACRONYM.sub(_spell_cyrillic, text)
        text = text.replace("—", "–")
        return re.sub(r"[ \t]+", " ", text).strip()
