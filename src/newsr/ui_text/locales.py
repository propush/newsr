from __future__ import annotations

import locale
import os
from dataclasses import dataclass
from typing import Final


DEFAULT_UI_LOCALE = "en"


@dataclass(frozen=True, slots=True)
class UILocaleDefinition:
    code: str
    name: str
    aliases: tuple[str, ...] = ()


PREDEFINED_UI_LOCALES: Final[tuple[UILocaleDefinition, ...]] = (
    UILocaleDefinition("en", "English", aliases=("english",)),
    UILocaleDefinition("ru", "Русский", aliases=("russian", "русский")),
)


_LOCALE_BY_CODE: Final[dict[str, UILocaleDefinition]] = {
    locale.code: locale
    for locale in PREDEFINED_UI_LOCALES
}

_LOCALE_BY_ALIAS: Final[dict[str, str]] = {
    alias: locale.code
    for locale in PREDEFINED_UI_LOCALES
    for alias in (locale.code, locale.name.lower(), *locale.aliases)
}


def available_ui_locale_names() -> tuple[str, ...]:
    return tuple(locale.name for locale in PREDEFINED_UI_LOCALES)


def resolve_ui_locale_name(value: str) -> str:
    locale_code = normalize_ui_locale(value)
    return _LOCALE_BY_CODE[locale_code].name


def normalize_ui_locale(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return DEFAULT_UI_LOCALE
    return _LOCALE_BY_ALIAS.get(normalized, DEFAULT_UI_LOCALE)


def parse_ui_locale(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    return _LOCALE_BY_ALIAS.get(normalized)


def guess_ui_locale(locale_name: str | None = None) -> str:
    resolved_locale = locale_name or _detect_locale_name()
    if not resolved_locale:
        return DEFAULT_UI_LOCALE
    normalized_locale = resolved_locale.split(".", 1)[0].split("@", 1)[0]
    language_code = normalized_locale.replace("-", "_").split("_", 1)[0].lower()
    if language_code in _LOCALE_BY_CODE:
        return language_code
    return DEFAULT_UI_LOCALE


def _detect_locale_name() -> str | None:
    for key in ("LC_ALL", "LC_CTYPE", "LANG"):
        value = os.environ.get(key)
        if value:
            return value
    try:
        detected_locale, _ = locale.getlocale()
    except ValueError:
        return None
    return detected_locale
