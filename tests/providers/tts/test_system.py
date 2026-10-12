from __future__ import annotations

from pathlib import Path

import pytest

from newsr.config import TTSSystemConfig
from newsr.providers.tts.base import TTSEngineError
from newsr.providers.tts.system import SystemTTSEngine, parse_say_voices

SAY_VOICES = """\
Albert              en_US    # Hello! My name is Albert.
Aman                en_IN    # Hello! My name is Aman.
Anna                de_DE    # Hallo! Ich heiße Anna.
Eddy (Russian (Russia)) ru_RU    # Привет.
Milena (Enhanced)   ru_RU    # Здравствуйте! Меня зовут Милена.
Samantha            en_US    # Hello! My name is Samantha.
"""


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, args, cancellation=None) -> str:  # type: ignore[no-untyped-def]
        args = list(args)
        self.commands.append(args)
        if args[:3] == ["say", "-v", "?"]:
            return SAY_VOICES
        output_flag = "-o" if args[0] == "say" else "-w"
        Path(args[args.index(output_flag) + 1]).write_bytes(b"RIFF-wav")
        return ""


def test_parse_say_voices_reads_names_with_spaces() -> None:
    assert parse_say_voices(SAY_VOICES)[3] == ("Eddy (Russian (Russia))", "ru_RU")


def test_system_engine_uses_say_with_auto_selected_voice_on_macos(tmp_path: Path) -> None:
    runner = FakeRunner()
    engine = SystemTTSEngine(TTSSystemConfig(), speed=1.5, platform="darwin", runner=runner, temp_dir=tmp_path)

    audio = engine.synthesize("Привет", "ru")

    assert audio.data == b"RIFF-wav"
    assert audio.format == "wav"
    command = runner.commands[-1]
    assert command[:5] == ["say", "-v", "Milena (Enhanced)", "-r", "270"]
    assert "--file-format=WAVE" in command
    assert engine.say_voice_for("en") == "Samantha"
    assert list(tmp_path.iterdir()) == []


def test_system_engine_uses_configured_voice_without_listing(tmp_path: Path) -> None:
    runner = FakeRunner()
    engine = SystemTTSEngine(
        TTSSystemConfig(voices={"en": "Daniel"}),
        speed=1.0,
        platform="darwin",
        runner=runner,
        temp_dir=tmp_path,
    )

    engine.synthesize("Hello", "en")

    assert runner.commands[0][:3] == ["say", "-v", "Daniel"]
    assert "-r" not in runner.commands[0]


def test_system_engine_uses_espeak_on_linux(tmp_path: Path) -> None:
    runner = FakeRunner()
    engine = SystemTTSEngine(
        TTSSystemConfig(),
        speed=2.0,
        platform="linux",
        runner=runner,
        which=lambda name: f"/usr/bin/{name}" if name == "espeak-ng" else None,
        temp_dir=tmp_path,
    )

    engine.synthesize("Hallo", "de")

    assert runner.commands[0][:5] == ["/usr/bin/espeak-ng", "-v", "de", "-s", "350"]


def test_system_engine_requires_espeak_off_macos(tmp_path: Path) -> None:
    engine = SystemTTSEngine(
        TTSSystemConfig(),
        speed=1.0,
        platform="linux",
        runner=FakeRunner(),
        which=lambda name: None,
        temp_dir=tmp_path,
    )

    with pytest.raises(TTSEngineError, match="espeak-ng"):
        engine.synthesize("Hello", "en")
