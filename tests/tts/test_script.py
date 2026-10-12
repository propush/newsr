from __future__ import annotations

from newsr.domain import ViewMode
from newsr.tts.script import SpeechSegment, body_language, build_item_script


def test_build_item_script_orders_intro_title_and_body_chunks() -> None:
    segments = build_item_script(
        intro="BBC News. Article 4 of 10",
        intro_language="en",
        title="**Big** news",
        body="First paragraph.\n\nSecond paragraph.",
        body_language="ru",
        max_chars=20,
    )

    assert segments == [
        SpeechSegment("BBC News. Article 4 of 10.", "en"),
        SpeechSegment("Big news.", "ru"),
        SpeechSegment("First paragraph.", "ru"),
        SpeechSegment("Second paragraph.", "ru"),
    ]


def test_body_language_uses_target_language_for_translated_modes() -> None:
    for mode in (ViewMode.FULL, ViewMode.SUMMARY):
        assert body_language(mode, "Hello", target_language="Russian", original_language="en") == "ru"


def test_body_language_detects_original_text() -> None:
    assert body_language(ViewMode.ORIGINAL, "Hello", target_language="Russian", original_language="en") == "en"
    assert body_language(ViewMode.ORIGINAL, "Привет", target_language="English", original_language="en") == "ru"


def test_body_language_detects_translated_text_for_unknown_language_names() -> None:
    assert body_language(ViewMode.FULL, "Привет", target_language="Klingon", original_language="en") == "ru"
    assert body_language(ViewMode.SUMMARY, "Hello", target_language="Klingon", original_language="en") is None
