from __future__ import annotations

import pytest

from newsr.config import TTSConfig, TTSElevenLabsConfig
from newsr.providers.tts import build_tts_engine
from newsr.providers.tts.edge import EdgeTTSEngine
from newsr.providers.tts.elevenlabs import ElevenLabsTTSEngine
from newsr.providers.tts.openai_compatible import OpenAICompatibleTTSEngine
from newsr.providers.tts.piper import PiperTTSEngine
from newsr.providers.tts.silero import SileroTTSEngine
from newsr.providers.tts.system import SystemTTSEngine


@pytest.mark.parametrize(
    ("engine", "expected"),
    [
        ("openai", OpenAICompatibleTTSEngine),
        ("elevenlabs", ElevenLabsTTSEngine),
        ("edge", EdgeTTSEngine),
        ("piper", PiperTTSEngine),
        ("system", SystemTTSEngine),
        ("silero", SileroTTSEngine),
    ],
)
def test_build_tts_engine_selects_configured_engine(engine: str, expected: type) -> None:
    config = TTSConfig(engine=engine, elevenlabs=TTSElevenLabsConfig(api_key="key", voices={"default": "v"}))

    assert isinstance(build_tts_engine(config), expected)


def test_build_tts_engine_passes_llm_transliteration_to_silero() -> None:
    class FakeLLM:
        def transliterate_terms(self, terms: list[str]) -> dict[str, str]:
            return {term: "этчед" for term in terms}

    engine = build_tts_engine(TTSConfig(engine="silero"), llm=FakeLLM())

    assert engine._llm_transliterate(["Etched"]) == {"Etched": "этчед"}
