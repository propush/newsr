from __future__ import annotations

from newsr.tts.language import detect_script_language, language_code


def test_language_code_maps_language_names_and_codes() -> None:
    assert language_code("Russian") == "ru"
    assert language_code(" german ") == "de"
    assert language_code("ru") == "ru"
    assert language_code("Klingon") is None
    assert language_code("") is None


def test_language_code_maps_languages_beyond_bootstrap_locales() -> None:
    assert language_code("Greek") == "el"
    assert language_code("Arabic") == "ar"
    assert language_code("Hindi") == "hi"
    assert language_code("Brazilian Portuguese") == "pt"
    assert language_code("Simplified Chinese") == "zh"
    assert language_code("pt-BR") == "pt"
    assert language_code("en_US") == "en"
    assert language_code("Русский") == "ru"


def test_detect_script_language_uses_script_and_latin_fallback() -> None:
    assert detect_script_language("Привет, мир", "en") == "ru"
    assert detect_script_language("Привіт, їжак", "en") == "uk"
    assert detect_script_language("Καλημέρα", "en") == "el"
    assert detect_script_language("東京の天気", "en") == "ja"
    assert detect_script_language("北京天气", "en") == "zh"
    assert detect_script_language("안녕하세요", "en") == "ko"
    assert detect_script_language("Hello world", "de") == "de"
    assert detect_script_language("BBC сообщает о новостях", "en") == "ru"
    assert detect_script_language("12345", "en") == "en"
    assert detect_script_language("नमस्ते दुनिया", "en") == "hi"
    assert detect_script_language("გამარჯობა", "en") == "ka"
