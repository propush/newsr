from __future__ import annotations

import pytest

from newsr.config import TTSEdgeConfig
from newsr.providers.tts.base import TTSEngineError
from newsr.providers.tts.edge import DEFAULT_EDGE_VOICE, EdgeTTSEngine

VOICES = [
    {"ShortName": "en-AU-NatashaNeural", "Locale": "en-AU"},
    {"ShortName": "en-US-AvaNeural", "Locale": "en-US"},
    {"ShortName": "de-DE-KatjaNeural", "Locale": "de-DE"},
    {"ShortName": "ru-RU-DmitryNeural", "Locale": "ru-RU"},
    {"ShortName": "ru-RU-SvetlanaNeural", "Locale": "ru-RU"},
]


def test_edge_engine_streams_audio_with_rate_and_discovered_voice() -> None:
    requests: list[tuple[str, str, str]] = []

    def stream(text: str, voice: str, rate: str, cancellation):  # type: ignore[no-untyped-def]
        requests.append((text, voice, rate))
        return [{"type": "audio", "data": b"one"}, {"type": "WordBoundary"}, {"type": "audio", "data": b"two"}]

    engine = EdgeTTSEngine(TTSEdgeConfig(), speed=1.2, stream=stream, list_voices=lambda: VOICES)

    audio = engine.synthesize("Привет", "ru")

    assert audio.data == b"onetwo"
    assert audio.format == "mp3"
    assert requests == [("Привет", "ru-RU-DmitryNeural", "+20%")]


def test_edge_engine_prefers_configured_then_main_region_then_default_voice() -> None:
    engine = EdgeTTSEngine(
        TTSEdgeConfig(voices={"de": "de-DE-ConradNeural"}),
        speed=1.0,
        list_voices=lambda: VOICES,
    )

    assert engine.voice_for("de") == "de-DE-ConradNeural"
    assert engine.voice_for("en") == "en-US-AvaNeural"
    assert engine.voice_for("ja") == DEFAULT_EDGE_VOICE
    assert engine.voice_for(None) == DEFAULT_EDGE_VOICE


def test_edge_engine_retries_voice_discovery_after_failure() -> None:
    calls: list[int] = []

    def flaky_list() -> list[dict[str, str]]:
        calls.append(1)
        if len(calls) == 1:
            raise OSError("offline")
        return VOICES

    engine = EdgeTTSEngine(TTSEdgeConfig(), speed=1.0, list_voices=flaky_list)

    assert engine.voice_for("ru") == DEFAULT_EDGE_VOICE
    assert engine.voice_for("ru") == "ru-RU-DmitryNeural"


def test_edge_engine_wraps_service_errors() -> None:
    def stream(text: str, voice: str, rate: str, cancellation):  # type: ignore[no-untyped-def]
        raise RuntimeError("websocket closed")

    engine = EdgeTTSEngine(TTSEdgeConfig(voices={"default": "x"}), speed=1.0, stream=stream, list_voices=lambda: [])

    with pytest.raises(TTSEngineError, match="websocket closed"):
        engine.synthesize("Hello", None)


def test_edge_engine_falls_back_to_next_voice_when_service_returns_no_audio() -> None:
    requests: list[str] = []

    def stream(text: str, voice: str, rate: str, cancellation):  # type: ignore[no-untyped-def]
        requests.append(voice)
        if voice == "ru-RU-DmitryNeural":
            return []
        return [{"type": "audio", "data": b"svetlana"}]

    engine = EdgeTTSEngine(TTSEdgeConfig(), speed=1.0, stream=stream, list_voices=lambda: VOICES)

    assert engine.synthesize("Рынки растут.", "ru").data == b"svetlana"
    assert engine.synthesize("Акции выросли.", "ru").data == b"svetlana"
    assert requests == ["ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural", "ru-RU-SvetlanaNeural"]
    assert engine.candidate_voices("ru") == ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural", DEFAULT_EDGE_VOICE]


def test_edge_engine_does_not_replace_a_configured_voice() -> None:
    def stream(text: str, voice: str, rate: str, cancellation):  # type: ignore[no-untyped-def]
        return []

    engine = EdgeTTSEngine(
        TTSEdgeConfig(voices={"ru": "ru-RU-DmitryNeural"}),
        speed=1.0,
        stream=stream,
        list_voices=lambda: VOICES,
    )

    with pytest.raises(TTSEngineError, match="no audio"):
        engine.synthesize("Рынки растут.", "ru")
