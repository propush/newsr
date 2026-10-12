from __future__ import annotations

import pytest

from newsr.config import TTSElevenLabsConfig, TTSOpenAIConfig
from newsr.providers.tts.base import TTSEngineError
from newsr.providers.tts.elevenlabs import ElevenLabsTTSEngine
from newsr.providers.tts.openai_compatible import OpenAICompatibleTTSEngine


class RecordingPost:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, url, payload, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append({"url": url, "payload": payload, **kwargs})
        return b"mp3"


def test_openai_engine_posts_speech_request_with_language_voice() -> None:
    post = RecordingPost()
    config = TTSOpenAIConfig(
        url="http://localhost:8880/v1",
        model="kokoro",
        api_key="secret",
        headers={"X-Org": "newsr"},
        voices={"default": "alloy", "ru": "nova"},
    )
    engine = OpenAICompatibleTTSEngine(config, speed=1.25, request_retries=3, post=post)

    audio = engine.synthesize("Привет", "ru")

    assert audio.data == b"mp3"
    assert audio.format == "mp3"
    call = post.calls[0]
    assert call["url"] == "http://localhost:8880/v1/audio/speech"
    assert call["payload"] == {
        "model": "kokoro",
        "input": "Привет",
        "voice": "nova",
        "response_format": "mp3",
        "speed": 1.25,
    }
    assert call["headers"] == {"Authorization": "Bearer secret", "X-Org": "newsr"}
    assert call["request_retries"] == 3


def test_openai_engine_falls_back_to_default_voice() -> None:
    post = RecordingPost()
    engine = OpenAICompatibleTTSEngine(TTSOpenAIConfig(), speed=1.0, request_retries=0, post=post)

    engine.synthesize("Hello", "de")

    assert post.calls[0]["payload"]["voice"] == "alloy"
    assert post.calls[0]["headers"] == {}


def test_elevenlabs_engine_posts_to_voice_endpoint_and_clamps_speed() -> None:
    post = RecordingPost()
    config = TTSElevenLabsConfig(api_key="xi-key", voices={"default": "voice/one", "ru": "ru-voice"})
    engine = ElevenLabsTTSEngine(config, speed=2.0, request_retries=1, post=post)

    engine.synthesize("Hello", "en")

    call = post.calls[0]
    assert call["url"] == (
        "https://api.elevenlabs.io/v1/text-to-speech/voice%2Fone?output_format=mp3_44100_128"
    )
    assert call["payload"] == {
        "text": "Hello",
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"speed": 1.2},
    }
    assert call["headers"]["xi-api-key"] == "xi-key"


def test_elevenlabs_engine_requires_a_voice() -> None:
    engine = ElevenLabsTTSEngine(TTSElevenLabsConfig(api_key="key"), speed=1.0, request_retries=0, post=RecordingPost())

    with pytest.raises(TTSEngineError, match="voices.default"):
        engine.synthesize("Hello", "en")
