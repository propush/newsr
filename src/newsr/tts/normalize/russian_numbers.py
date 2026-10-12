from __future__ import annotations

import re
from functools import cache

from num2words import num2words

N2W_CASES = {
    "nomn": "nominative",
    "gent": "genitive",
    "datv": "dative",
    "accs": "accusative",
    "ablt": "instrumental",
    "loct": "prepositional",
}
PREPOSITION_CASES = {
    **dict.fromkeys(
        "до от из без для около более менее свыше после кроме среди порядка у против вместо вокруг ради вроде".split(),
        "gent",
    ),
    **dict.fromkeys("к ко благодаря согласно вопреки".split(), "datv"),
    **dict.fromkeys("о об при".split(), "loct"),
    **dict.fromkeys("между над под перед".split(), "ablt"),
    **dict.fromkeys("за про через".split(), "accs"),
}
UNITS = {
    "млн": "миллион",
    "млрд": "миллиард",
    "трлн": "триллион",
    "тыс": "тысяча",
    "%": "процент",
    "ТБ": "терабайт",
    "ГБ": "гигабайт",
    "МБ": "мегабайт",
    "КБ": "килобайт",
    "Гбит/с": "гигабит в секунду",
    "Мбит/с": "мегабит в секунду",
    "Тбит/с": "терабит в секунду",
    "ГБ/с": "гигабайт в секунду",
    "МБ/с": "мегабайт в секунду",
    "ГГц": "гигагерц",
    "МГц": "мегагерц",
    "Гц": "герц",
    "Вт": "ватт",
    "кВт": "киловатт",
    "МВт": "мегаватт",
    "ГВт": "гигаватт",
    "мАч": "миллиампер-час",
    "км": "километр",
    "см": "сантиметр",
    "мм": "миллиметр",
    "нм": "нанометр",
    "кг": "килограмм",
    "руб": "рубль",
    "долл": "доллар",
}
CURRENCY_SIGNS = {"$": "доллар", "€": "евро", "£": "фунт", "₽": "рубль", "¥": "иена"}
# Counted multipliers: the currency noun after them stays genitive plural ("семьсот миллионов долларов").
MULTIPLIERS = {"миллион", "миллиард", "триллион", "тысяча"}
MONTHS_GENITIVE = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)

_UNIT_PATTERN = "|".join(sorted((re.escape(unit) for unit in UNITS), key=len, reverse=True))
_NUMBER = r"\d+(?:[.,]\d+)?"
_NUMBER_RE = re.compile(
    rf"(?:(?P<sign>[$€£₽¥])\s?)?(?P<num>{_NUMBER})(?:\s?[–—-]\s?(?P<num2>{_NUMBER}))?"
    rf"(?:\s?(?P<unit>{_UNIT_PATTERN})(?![А-Яа-яЁёA-Za-z])(?:\.(?=\s*[а-яё]))?)?(?:\s?(?P<sign_after>[$€£₽¥]))?"
)
_YEAR = r"(?:1[89]|20|21)\d\d"
_YEAR_RE = re.compile(rf"\b(?P<year>{_YEAR})(?:\s?[–—-]\s?(?P<year2>{_YEAR}))?\s+(?P<word>год[а-я]*|гг?\.)")
_DATE_RE = re.compile(
    rf"\b(?:(?P<first>[0-3]?\d)\s*(?P<sep>[–—-]|по|до)\s*)?(?P<day>[0-3]?\d)\s+(?P<month>{'|'.join(MONTHS_GENITIVE)})\b"
)
_ORDINAL_RE = re.compile(r"\b(?P<num>\d+)-(?P<suffix>й|я|е|го|му|м|х|ми|ю|ое|ая|ый|ий|ой|ом|ых|ым|ые|ую)\b")
_TIME_RE = re.compile(r"\b(?P<hours>[01]?\d|2[0-3]):(?P<minutes>[0-5]\d)\b")
_GROUPED_DIGITS_RE = re.compile(r"(?<=\d)[   ](?=\d{3}\b)")
_WORD_RE = re.compile(r"[А-Яа-яЁё+]+")
_DECIMAL_RE = re.compile(r"\d+[.,]\d+")


@cache
def _morph():
    import pymorphy3

    return pymorphy3.MorphAnalyzer()


def _words_before(text: str, end: int) -> list[str]:
    return [word.replace("+", "").lower() for word in _WORD_RE.findall(text[max(0, end - 60):end])]


def _word_after(text: str, start: int) -> str | None:
    match = _WORD_RE.search(text, start, min(len(text), start + 40))
    return match.group(0).replace("+", "") if match else None


def _noun_parse(word: str | None):
    if not word:
        return None
    return next((parse for parse in _morph().parse(word) if parse.tag.POS == "NOUN"), None)


def _noun_case(parse) -> str | None:
    if parse is None:
        return None
    case = parse.tag.case
    return {"loc2": "loct", "gen2": "gent", "acc2": "accs"}.get(case, case)


def numeral_case(text: str, start: int, end: int, noun: str | None) -> str:
    """Grammatical case of a number, from the preposition before it and the noun after it."""
    before = _words_before(text, start)
    preposition = before[-1] if before else ""
    noun_parse = _noun_parse(noun)
    noun_case = _noun_case(noun_parse)
    if preposition in PREPOSITION_CASES:
        return PREPOSITION_CASES[preposition]
    if preposition in {"в", "во", "на"}:
        return "loct" if noun_case == "loct" else "accs"
    if preposition in {"с", "со"}:
        return "gent" if re.search(r"\b(до|по)\b", text[end:end + 40]) else "ablt"
    if preposition == "по":
        return "datv" if noun_case == "datv" else "accs"
    if noun_case in {"datv", "ablt", "loct"}:
        return noun_case
    if noun_case == "accs" and noun_parse.tag.number == "sing":
        return "accs"
    return "nomn"


def _gender(parse) -> str:
    if parse is None:
        return "m"
    return {"femn": "f", "neut": "n"}.get(parse.tag.gender, "m")


def _inflect_word(word: str, case: str) -> str:
    parse = next((p for p in _morph().parse(word) if p.tag.POS in {"NUMR", "ADJF", "NOUN"}), None)
    if parse is None:
        return word
    form = parse.inflect({case}) or parse.inflect({case, "plur"})
    return form.word if form else word


def cardinal(value: str, case: str = "nomn", gender: str = "m") -> str:
    if _DECIMAL_RE.fullmatch(value):
        words = num2words(float(value.replace(",", ".")), lang="ru").split()
        if case in {"nomn", "accs"}:
            return " ".join(words)
        return " ".join(_inflect_word(word, case) for word in words)
    number = int(value)
    if case == "accs":
        # Counted nouns are inanimate: the accusative matches the nominative, except feminine "одну".
        spoken = num2words(number, lang="ru", gender=gender)
        if gender == "f" and number % 10 == 1 and number % 100 != 11:
            spoken = spoken.removesuffix("одна") + "одну"
        return spoken
    return num2words(number, lang="ru", case=N2W_CASES[case], gender=gender)


def agree(noun: str, value: str, case: str) -> str:
    """Inflect a counted noun to agree with the number before it."""
    if noun == "евро":
        return noun
    if " " in noun:
        first, rest = noun.split(" ", 1)
        return f"{agree(first, value, case)} {rest}"
    head, _, tail = noun.partition("-")
    target = tail or head
    parse = _noun_parse(target)
    if parse is None:
        return noun
    if _DECIMAL_RE.fullmatch(value):
        form = parse.inflect({"gent", "sing"})
    else:
        number = int(value)
        single = number % 10 == 1 and number % 100 != 11
        if case == "accs" and single:
            form = parse.inflect({"accs", "sing"})
        elif case in {"nomn", "accs"}:
            form = parse.make_agree_with_number(number)
        else:
            form = parse.inflect({case, "sing" if single else "plur"})
    word = form.word if form else target
    return f"{head}-{word}" if tail else word


def _replace_year(match: re.Match[str], text: str) -> str:
    word = match.group("word")
    before = _words_before(text, match.start())
    preposition = before[-1] if before else ""
    if word in {"г.", "гг."}:
        if match.group("year2"):
            word = "годах" if preposition in {"в", "во"} else "годов"
        else:
            word = "году" if preposition in {"в", "во", "о", "при"} else "года"
    case = _noun_case(_noun_parse(word)) or "nomn"
    if word == "году" and preposition in {"к", "ко", "по"}:
        case = "datv"
    years = [match.group("year")] + ([match.group("year2")] if match.group("year2") else [])
    spoken = " — ".join(num2words(int(year), lang="ru", to="ordinal", case=N2W_CASES[case]) for year in years)
    return f"{spoken} {word}"


def _replace_date(match: re.Match[str], text: str) -> str:
    before = _words_before(text, match.start())
    case = {"к": "datv", "ко": "datv", "по": "accs"}.get(before[-1] if before else "", "gent")
    first = ""
    if match.group("first"):
        separator = match.group("sep") if match.group("sep") in {"по", "до"} else "—"
        first_day = num2words(int(match.group("first")), lang="ru", to="ordinal", case="genitive", gender="n")
        first = f"{first_day} {separator} "
        case = {"по": "accs", "до": "gent"}.get(separator, "gent")
    day = num2words(int(match.group("day")), lang="ru", to="ordinal", case=N2W_CASES[case], gender="n")
    return f"{first}{day} {match.group('month')}"


def _replace_ordinal(match: re.Match[str], text: str) -> str:
    words = num2words(int(match.group("num")), lang="ru", to="ordinal").split()
    suffix = match.group("suffix")
    preferred = numeral_case(text, match.start(), match.end(), _word_after(text, match.end()))
    parse = next((p for p in _morph().parse(words[-1]) if p.tag.POS == "ADJF"), None)
    if parse is not None:
        forms = sorted(
            (form for form in parse.lexeme if form.word.endswith(suffix)),
            key=lambda form: form.tag.case != preferred,
        )
        if forms:
            words[-1] = forms[0].word
    return " ".join(words)


def _replace_time(match: re.Match[str]) -> str:
    minutes = match.group("minutes")
    spoken_minutes = "ноль ноль" if minutes == "00" else cardinal(minutes.lstrip("0") or "0")
    return f"{cardinal(match.group('hours'))} {spoken_minutes}"


def _replace_number(match: re.Match[str], text: str) -> str:
    num, num2 = match.group("num"), match.group("num2")
    unit = UNITS.get(match.group("unit") or "")
    sign = match.group("sign") or match.group("sign_after")
    currency = CURRENCY_SIGNS.get(sign) if sign else None
    head_noun = unit or currency or _word_after(text, match.end())
    case = numeral_case(text, match.start(), match.end(), head_noun)
    gender = _gender(_noun_parse(head_noun))
    parts = [cardinal(num, case, gender)]
    if num2:
        parts += ["—", cardinal(num2, case, gender)]
    last = num2 or num
    if unit:
        parts.append(agree(unit, last, case))
    if currency:
        parts.append(agree(currency, "5", "nomn") if unit in MULTIPLIERS else agree(currency, last, case))
    return " ".join(parts)


def russian_numbers_to_words(text: str) -> str:
    """Write numbers, years, dates, times, units, and currency amounts as Russian words."""
    text = _GROUPED_DIGITS_RE.sub("", text)
    text = _YEAR_RE.sub(lambda match: _replace_year(match, text), text)
    text = _DATE_RE.sub(lambda match: _replace_date(match, text), text)
    text = _ORDINAL_RE.sub(lambda match: _replace_ordinal(match, text), text)
    text = _TIME_RE.sub(_replace_time, text)
    text = text.replace("×", " на ").replace("№", "номер ").replace("#", "номер ")
    # One number at a time, so case detection sees already converted neighbours.
    while (match := _NUMBER_RE.search(text)) is not None:
        text = text[:match.start()] + _replace_number(match, text) + text[match.end():]
    return text
