from __future__ import annotations

from pathlib import Path

import pytest

from newsr.config import load_config

BASE_CONFIG = """
llm:
  url: http://localhost:8081/v1
  model_translation: translate
  model_summary: summary
translation:
  target_language: Russian
ui:
  locale: en
"""


def write_config(tmp_path: Path, tts_section: str = "") -> Path:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(BASE_CONFIG + tts_section, encoding="utf-8")
    return config_path


def test_load_config_uses_tts_defaults_when_section_is_missing(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))

    assert config.tts.engine == "edge"
    assert config.tts.speed == 1.0
    assert config.tts.original_language == "en"
    assert config.tts.request_retries == 2
    assert config.tts.media_controls is True
    assert config.tts.openai.url == "https://api.openai.com/v1"
    assert config.tts.openai.model == "gpt-4o-mini-tts"
    assert config.tts.elevenlabs.model == "eleven_multilingual_v2"
    assert config.tts.piper.models_dir == "cache/piper"
    assert config.tts.edge.voices == {}
    assert config.tts.silero.models_dir == "cache/silero"
    assert config.tts.silero.voices == {}
    assert config.tts.silero.lexicon == {}


def test_load_config_reads_every_tts_engine_block(tmp_path: Path) -> None:
    config = load_config(
        write_config(
            tmp_path,
            """
tts:
  engine: OpenAI
  speed: 1.25
  original_language: DE
  request_retries: 4
  openai:
    url: http://localhost:8880/v1/
    model: kokoro
    api_key: sk-test
    headers:
      X-Org: newsr
    voices:
      default: af_heart
      RU: nova
  elevenlabs:
    api_key: xi-test
    model: eleven_flash_v2_5
    voices:
      default: voice-id
  edge:
    voices:
      ru: ru-RU-SvetlanaNeural
  piper:
    models_dir: /opt/piper
    voices:
      en: en_US-amy-medium
  system:
    voices:
      ru: Milena
  silero:
    models_dir: /opt/silero
    voices:
      RU: baya
      en: en_12
    lexicon:
      Issue: +ишью
      США: сэ-шэ-+а
""",
        )
    )

    tts = config.tts
    assert tts.engine == "openai"
    assert tts.speed == 1.25
    assert tts.original_language == "de"
    assert tts.request_retries == 4
    assert tts.openai.url == "http://localhost:8880/v1"
    assert tts.openai.model == "kokoro"
    assert tts.openai.api_key == "sk-test"
    assert tts.openai.headers == {"X-Org": "newsr"}
    assert tts.openai.voices == {"default": "af_heart", "ru": "nova"}
    assert tts.elevenlabs.api_key == "xi-test"
    assert tts.elevenlabs.model == "eleven_flash_v2_5"
    assert tts.edge.voices == {"ru": "ru-RU-SvetlanaNeural"}
    assert tts.piper.models_dir == "/opt/piper"
    assert tts.piper.voices == {"en": "en_US-amy-medium"}
    assert tts.system.voices == {"ru": "Milena"}
    assert tts.silero.models_dir == "/opt/silero"
    assert tts.silero.voices == {"ru": "baya", "en": "en_12"}
    assert tts.silero.lexicon == {"Issue": "+ишью", "США": "сэ-шэ-+а"}


@pytest.mark.parametrize(
    ("tts_section", "message"),
    [
        ("tts:\n  engine: festival\n", "tts.engine must be one of"),
        ("tts:\n  speed: 3\n", "tts.speed must be between"),
        ("tts:\n  speed: fast\n", "tts.speed must be a number"),
        ("tts:\n  request_retries: -1\n", "tts.request_retries must be non-negative"),
        ("tts:\n  original_language: ' '\n", "tts.original_language"),
        ("tts: edge\n", "tts must be a mapping"),
        ("tts:\n  edge:\n    voices: [a]\n", "tts.edge.voices must be a mapping"),
        ("tts:\n  edge:\n    voices:\n      ru: ''\n", "tts.edge.voices keys and values"),
        ("tts:\n  engine: elevenlabs\n", "tts.elevenlabs.api_key is required"),
        ("tts:\n  silero:\n    models_dir: ' '\n", "tts.silero.models_dir must be non-empty"),
        ("tts:\n  silero:\n    lexicon: [a]\n", "tts.silero.lexicon must be a mapping"),
        ("tts:\n  silero:\n    lexicon:\n      Issue: ''\n", "tts.silero.lexicon keys and values"),
        (
            "tts:\n  engine: elevenlabs\n  elevenlabs:\n    api_key: key\n",
            "tts.elevenlabs.voices.default is required",
        ),
    ],
)
def test_load_config_rejects_invalid_tts_values(tmp_path: Path, tts_section: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_config(write_config(tmp_path, tts_section))


def test_load_config_reads_tts_media_controls_switch(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, "\ntts:\n  media_controls: false\n"))

    assert config.tts.media_controls is False


def test_load_config_rejects_non_boolean_tts_media_controls(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="tts.media_controls must be true or false"):
        load_config(write_config(tmp_path, "\ntts:\n  media_controls: sometimes\n"))
