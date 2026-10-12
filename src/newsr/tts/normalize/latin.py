"""Rewrite English names, brands, versions, and acronyms inside Russian text in Cyrillic."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from .russian_numbers import MONTHS_GENITIVE, UNITS, cardinal

LETTER_NAMES = {
    "a": "эй", "b": "би", "c": "си", "d": "ди", "e": "и", "f": "эф", "g": "джи", "h": "эйч", "i": "ай",
    "j": "джей", "k": "кей", "l": "эл", "m": "эм", "n": "эн", "o": "оу", "p": "пи", "q": "кью", "r": "ар",
    "s": "эс", "t": "ти", "u": "ю", "v": "ви", "w": "дабл-ю", "x": "экс", "y": "уай", "z": "зед",
}
SYMBOLS = {"&": "энд", "+": "плюс", "/": "и"}
STOPWORDS = frozenset({"the", "a", "an", "of"})

# A run of Latin tokens; numbers, inner dots, slashes, and apostrophes may sit inside ("Pixel 10 Pro XL", "Beta 6.1").
_TOKEN_TAIL = r"(?:[A-Za-z0-9'’&+/-]|\.(?=[A-Za-z0-9]))*"
_SPAN_RE = re.compile(rf"(?<![А-Яа-яЁё])[A-Za-z]{_TOKEN_TAIL}(?:[ \t]+[A-Za-z0-9]{_TOKEN_TAIL})*")
_PART_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?|\d+(?:\.\d+)*|[&+/]")
_ACRONYM_RE = re.compile(r"[A-Z]{2,}s?|[A-Za-z]")
# A number that ends a Latin span belongs to the Russian text when a month or unit follows ("Ultra 28 сентября").
_RUSSIAN_CONTINUATION = re.compile(
    r"\s*(?:" + "|".join([*MONTHS_GENITIVE, *(re.escape(unit) for unit in UNITS)]) + r")(?![А-Яа-яЁё])"
)
_TRAILING_NUMBER = re.compile(r"[ \t]+\d+(?:[.,]\d+)?$")
_VOWEL = re.compile(r"[аеёиоуыэюя]")

Part = tuple[str, str]
Transliterate = Callable[[list[str]], Mapping[str, str]]


def stress_last(letters: list[str]) -> str:
    """Join spelled letters, stressing the last one: "ти-эс-эм-с+и"."""
    last = letters[-1]
    vowel = _VOWEL.search(last)
    if vowel and "+" not in last:
        letters = [*letters[:-1], last[:vowel.start()] + "+" + last[vowel.start():]]
    return "-".join(letters)


def spell_latin(acronym: str) -> str:
    plural = acronym.endswith("s") and len(acronym) > 2 and acronym[:-1].isupper()
    letters = [LETTER_NAMES[char] for char in (acronym[:-1] if plural else acronym).lower()]
    return stress_last([*letters, "эс"] if plural else letters)


def number_in_name(value: str) -> str:
    # Versions inside names are read with "точка": "шесть точка один".
    return " точка ".join(cardinal(part) for part in value.split("."))


def classify(span: str) -> list[Part]:
    """Split a Latin span into ("word" | "acronym" | "number" | "symbol", text) parts."""
    parts: list[Part] = []
    for raw in re.split(r"[\s-]+", span):
        for token in _PART_RE.findall(raw):
            if token[0].isdigit():
                parts.append(("number", token))
            elif token in SYMBOLS:
                parts.append(("symbol", token))
            elif _ACRONYM_RE.fullmatch(token):
                parts.append(("acronym", token))
            else:
                parts.append(("word", token))
    return parts


def _key(phrase: str) -> tuple[str, ...]:
    return tuple(text.lower() for _, text in classify(phrase))


def _without_articles(part: Part) -> Part:
    kind, text = part
    if kind != "run":
        return part
    words = text.split()
    while words and words[0].lower() in STOPWORDS:
        words.pop(0)
    return kind, " ".join(words)


class LatinRewriter:
    """Replace Latin spans with Cyrillic: pronunciations first, spelled acronyms, numbers, transliterated words."""

    def __init__(self, pronunciations: Mapping[str, str], transliterate: Transliterate) -> None:
        self._pronunciations = {_key(term): spoken for term, spoken in pronunciations.items() if _key(term)}
        self._longest = max((len(key) for key in self._pronunciations), default=1)
        self._transliterate = transliterate

    def rewrite(self, text: str) -> str:
        positions = self._spans(text)
        spans = [self._resolve(classify(text[start:end].rstrip("-/"))) for start, end in positions]
        runs = sorted({value for parts in spans for kind, value in parts if kind == "run"})
        known = dict(self._transliterate(runs)) if runs else {}
        for (start, end), parts in zip(reversed(positions), reversed(spans)):
            trailing = text[start:end][len(text[start:end].rstrip("-/")):]
            text = text[:start] + self._speak(parts, known) + trailing + text[end:]
        return text

    def _spans(self, text: str) -> list[tuple[int, int]]:
        spans = []
        for match in _SPAN_RE.finditer(text):
            start, end = match.span()
            trailing = _TRAILING_NUMBER.search(text, start, end)
            if trailing and _RUSSIAN_CONTINUATION.match(text, end):
                end = trailing.start()
            spans.append((start, end))
        return spans

    def _resolve(self, parts: list[Part]) -> list[Part]:
        """Replace known phrases with ("spoken", text) and join remaining words into ("run", text)."""
        resolved: list[Part] = []
        index = 0
        while index < len(parts):
            for size in range(min(self._longest, len(parts) - index), 0, -1):
                key = tuple(text.lower() for _, text in parts[index:index + size])
                if key in self._pronunciations:
                    resolved.append(("spoken", self._pronunciations[key]))
                    index += size
                    break
            else:
                kind, text = parts[index]
                if kind == "word" and resolved and resolved[-1][0] == "run":
                    resolved[-1] = ("run", f"{resolved[-1][1]} {text}")
                elif kind == "word":
                    resolved.append(("run", text))
                else:
                    resolved.append((kind, text))
                index += 1
        return [part for part in map(_without_articles, resolved) if part[1]]

    @staticmethod
    def _speak(parts: list[Part], known: Mapping[str, str]) -> str:
        spoken: list[str] = []
        for kind, value in parts:
            if kind == "spoken":
                spoken.append(value)
            elif kind == "run":
                spoken.append(known.get(value) or " ".join(spell_latin(word) for word in value.split()))
            elif kind == "number":
                spoken.append(number_in_name(value))
            elif kind == "symbol":
                spoken.append(SYMBOLS[value])
            else:
                spoken.append(spell_latin(value))
        return " ".join(spoken)
