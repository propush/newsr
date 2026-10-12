"""English text for Silero's English voices: numbers, symbols, and acronyms as words."""

from __future__ import annotations

import re

from num2words import num2words

ENGLISH_LETTER_NAMES = {
    "a": "ay", "b": "bee", "c": "see", "d": "dee", "e": "ee", "f": "eff", "g": "gee", "h": "aitch", "i": "eye",
    "j": "jay", "k": "kay", "l": "el", "m": "em", "n": "en", "o": "oh", "p": "pee", "q": "cue", "r": "ar",
    "s": "ess", "t": "tee", "u": "you", "v": "vee", "w": "double-you", "x": "ex", "y": "why", "z": "zee",
}
# Acronyms read as words; all others are spelled letter by letter.
ENGLISH_WORD_ACRONYMS = frozenset({
    "NASA", "NATO", "UNESCO", "UNICEF", "OPEC", "IKEA", "CERN", "FIFA", "UEFA", "LEGO",
    "NAND", "RAM", "ROM", "SIM", "PIN", "LAN", "GIF", "COVID", "ASAP", "SCOTUS",
})
MAGNITUDES = {"k": "thousand", "m": "million", "mn": "million", "bn": "billion", "b": "billion", "tn": "trillion"}
CURRENCIES = {"$": "dollars", "€": "euros", "£": "pounds", "¥": "yen", "₽": "rubles"}
UNITS = {
    "TB": "terabytes", "GB": "gigabytes", "MB": "megabytes", "KB": "kilobytes",
    "Tbps": "terabits per second", "Gbps": "gigabits per second", "Mbps": "megabits per second",
    "GHz": "gigahertz", "MHz": "megahertz", "mAh": "milliamp hours", "kWh": "kilowatt hours",
    "kW": "kilowatts", "MW": "megawatts", "GW": "gigawatts", "W": "watts",
    "km": "kilometers", "mm": "millimeters", "nm": "nanometers", "kg": "kilograms",
}

_MONEY_RE = re.compile(
    r"(?P<sign>[$€£¥₽])\s?(?P<num>\d+(?:\.\d+)?)"
    r"(?:\s?(?P<magnitude>thousand|million|billion|trillion|bn|mn|tn|[kmb])\b)?",
    re.IGNORECASE,
)
_UNIT_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s?(?P<unit>" + "|".join(sorted(map(re.escape, UNITS), key=len, reverse=True)) + r")\b"
)
_PERCENT_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s?%")
_ORDINAL_RE = re.compile(r"\b(?P<num>\d+)(?:st|nd|rd|th)\b")
_YEAR_RE = re.compile(r"\b(?P<year>1[1-9]\d\d|20\d\d)(?P<plural>s)?\b")
_TIME_RE = re.compile(r"\b(?P<hours>[01]?\d|2[0-3]):(?P<minutes>[0-5]\d)\b")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_GROUPED_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}s?\b")
_LETTER_DIGIT_RE = re.compile(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])")
_SINGLE_LETTER_RE = re.compile(r"\b(?![AI]\b)[A-Z]\b")


def _number(value: str) -> str:
    if "." in value:
        whole, fraction = value.split(".", 1)
        return f"{num2words(int(whole), lang='en')} point {' '.join(num2words(int(digit), lang='en') for digit in fraction)}"
    return num2words(int(value), lang="en")


def _money(match: re.Match[str]) -> str:
    magnitude = (match.group("magnitude") or "").lower()
    spoken_magnitude = MAGNITUDES.get(magnitude, magnitude)
    currency = CURRENCIES[match.group("sign")]
    return " ".join(part for part in (_number(match.group("num")), spoken_magnitude, currency) if part)


def _year(match: re.Match[str]) -> str:
    spoken = num2words(int(match.group("year")), lang="en", to="year")
    if match.group("plural"):
        spoken = spoken[:-1] + "ies" if spoken.endswith("y") else spoken + "s"
    return spoken


def _acronym(match: re.Match[str]) -> str:
    token = match.group(0)
    plural = token.endswith("s")
    letters = token[:-1] if plural else token
    if letters in ENGLISH_WORD_ACRONYMS:
        return token.lower()
    spoken = "-".join(ENGLISH_LETTER_NAMES[char] for char in letters.lower())
    return f"{spoken}s" if plural else spoken


def normalize_english(text: str) -> str:
    """Prepare English text for a voice that reads letters and punctuation only."""
    text = re.sub(r"[\[\]«»“”„\"()+*_`#]", "", text)
    text = _GROUPED_RE.sub(lambda match: num2words(int(match.group(0).replace(",", "")), lang="en"), text)
    text = _MONEY_RE.sub(_money, text)
    text = _PERCENT_RE.sub(lambda match: f"{_number(match.group('num'))} percent", text)
    text = _UNIT_RE.sub(lambda match: f"{_number(match.group('num'))} {UNITS[match.group('unit')]}", text)
    text = _ORDINAL_RE.sub(lambda match: num2words(int(match.group("num")), lang="en", to="ordinal"), text)
    text = _TIME_RE.sub(lambda match: f"{_number(match.group('hours'))} {_number(match.group('minutes'))}", text)
    text = _YEAR_RE.sub(_year, text)
    text = _LETTER_DIGIT_RE.sub(" ", text)
    text = _NUMBER_RE.sub(lambda match: _number(match.group(0)), text)
    text = _ACRONYM_RE.sub(_acronym, text)
    text = _SINGLE_LETTER_RE.sub(lambda match: ENGLISH_LETTER_NAMES[match.group(0).lower()], text)
    text = text.replace("&", " and ").replace("—", ", ").replace("–", ", ").replace("…", ".")
    return re.sub(r"[ \t]+", " ", text).strip()
