from __future__ import annotations

from newsr.ui_text import (
    UILocalizer,
    available_ui_locale_names,
    guess_ui_locale,
    normalize_ui_locale,
    parse_ui_locale,
    resolve_ui_locale_name,
)


def test_ui_locale_helpers_accept_russian_names_and_locale_codes() -> None:
    assert normalize_ui_locale("ru") == "ru"
    assert parse_ui_locale("russian") == "ru"
    assert parse_ui_locale("Русский") == "ru"
    assert resolve_ui_locale_name("ru") == "Русский"
    assert guess_ui_locale("ru_RU.UTF-8") == "ru"
    assert available_ui_locale_names() == ("English", "Русский")


def test_ui_localizer_returns_russian_translations_and_keeps_status_mapping() -> None:
    ui = UILocalizer("ru")

    assert ui.text("app.binding.summary") == "Сводка"
    assert ui.text("quick_nav.selection", current=2, total=5) == "Выбрано 2 из 5"
    assert ui.status("ready") == "готово"
    assert ui.status("searching DuckDuckGo...") == "поиск в DuckDuckGo..."
