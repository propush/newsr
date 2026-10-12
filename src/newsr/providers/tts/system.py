from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from threading import Lock
from time import monotonic

from ...cancellation import RefreshCancellation
from ...config.models import TTSSystemConfig
from .base import LOGGER, SynthesizedAudio, TTSEngineError, configure_tts_logger
from .voices import preferred_locale

COMMAND_TIMEOUT_SECONDS = 120
DEFAULT_SAY_RATE = 180
DEFAULT_ESPEAK_RATE = 175
TEMP_DIR = Path("cache") / "tts"
_SAY_VOICE_LINE = re.compile(r"^(?P<name>.+?)\s+(?P<locale>[a-z]{2,3}_[A-Za-z0-9]+)\s+#")
# Novelty and Eloquence voices sound robotic; they are skipped when a voice is chosen automatically.
_SKIPPED_SAY_VOICES = {
    "albert", "bad news", "bahh", "bells", "boing", "bubbles", "cellos", "eddy", "flo", "fred",
    "good news", "grandma", "grandpa", "jester", "junior", "kathy", "organ", "ralph", "reed",
    "rocko", "sandy", "shelley", "superstar", "trinoids", "whisper", "wobble", "zarvox",
}

CommandRunner = Callable[[Sequence[str], RefreshCancellation | None], str]


def run_command(args: Sequence[str], cancellation: RefreshCancellation | None) -> str:
    try:
        process = subprocess.Popen(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise TTSEngineError(f"could not run {args[0]}: {exc}") from exc
    deadline = monotonic() + COMMAND_TIMEOUT_SECONDS
    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.1)
            break
        except subprocess.TimeoutExpired:
            if (cancellation is not None and cancellation.is_cancelled) or monotonic() > deadline:
                process.kill()
                process.communicate()
                if cancellation is not None:
                    cancellation.raise_if_cancelled()
                raise TTSEngineError(f"{args[0]} timed out") from None
    if process.returncode != 0:
        raise TTSEngineError(f"{args[0]} failed: {stderr.strip() or process.returncode}")
    return stdout


def parse_say_voices(output: str) -> list[tuple[str, str]]:
    voices: list[tuple[str, str]] = []
    for line in output.splitlines():
        match = _SAY_VOICE_LINE.match(line)
        if match is not None:
            voices.append((match.group("name").strip(), match.group("locale")))
    return voices


class SystemTTSEngine:
    name = "system"
    max_chars = 1000

    def __init__(
        self,
        config: TTSSystemConfig,
        *,
        speed: float,
        platform: str = sys.platform,
        runner: CommandRunner = run_command,
        which: Callable[[str], str | None] = shutil.which,
        temp_dir: Path = TEMP_DIR,
    ) -> None:
        self._config = config
        self._speed = speed
        self._platform = platform
        self._runner = runner
        self._which = which
        self._temp_dir = temp_dir
        self._say_voices: list[tuple[str, str]] | None = None
        self._lock = Lock()

    def synthesize(
        self,
        text: str,
        language: str | None,
        cancellation: RefreshCancellation | None = None,
    ) -> SynthesizedAudio:
        configure_tts_logger()
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self._temp_dir) as work_dir:
            text_path = Path(work_dir) / "input.txt"
            audio_path = Path(work_dir) / "output.wav"
            text_path.write_text(text, encoding="utf-8")
            args = self._command(text_path, audio_path, language, cancellation)
            LOGGER.info("synthesis_start engine=system command=%s text_chars=%s", args[0], len(text))
            self._runner(args, cancellation)
            if not audio_path.exists() or audio_path.stat().st_size == 0:
                raise TTSEngineError(f"{args[0]} produced no audio")
            return SynthesizedAudio(data=audio_path.read_bytes(), format="wav")

    def _command(
        self,
        text_path: Path,
        audio_path: Path,
        language: str | None,
        cancellation: RefreshCancellation | None,
    ) -> list[str]:
        if self._platform == "darwin":
            args = ["say"]
            voice = self.say_voice_for(language, cancellation)
            if voice:
                args += ["-v", voice]
            if self._speed != 1.0:
                args += ["-r", str(round(DEFAULT_SAY_RATE * self._speed))]
            return args + [
                "--file-format=WAVE",
                "--data-format=LEI16@22050",
                "-o",
                str(audio_path),
                "-f",
                str(text_path),
            ]
        binary = self._which("espeak-ng") or self._which("espeak")
        if binary is None:
            raise TTSEngineError("system voices need espeak-ng on this platform")
        args = [binary]
        voice = self._configured_voice(language) or language
        if voice:
            args += ["-v", voice]
        if self._speed != 1.0:
            args += ["-s", str(round(DEFAULT_ESPEAK_RATE * self._speed))]
        return args + ["-w", str(audio_path), "-f", str(text_path)]

    def say_voice_for(self, language: str | None, cancellation: RefreshCancellation | None = None) -> str | None:
        configured = self._configured_voice(language)
        if configured or not language:
            return configured
        language = language.lower()
        preferred = preferred_locale(language)
        candidates = [
            (name, locale)
            for name, locale in self._list_say_voices(cancellation)
            if locale.split("_", 1)[0].lower() == language
            and name.split(" (", 1)[0].strip().lower() not in _SKIPPED_SAY_VOICES
        ]
        candidates.sort(key=lambda candidate: candidate[1] != preferred)
        if candidates:
            return candidates[0][0]
        return self._config.voices.get("default")

    def _configured_voice(self, language: str | None) -> str | None:
        voices = self._config.voices
        if language and language.lower() in voices:
            return voices[language.lower()]
        if not language:
            return voices.get("default")
        return None

    def _list_say_voices(self, cancellation: RefreshCancellation | None) -> list[tuple[str, str]]:
        with self._lock:
            if self._say_voices is None:
                try:
                    self._say_voices = parse_say_voices(self._runner(["say", "-v", "?"], cancellation))
                except TTSEngineError as exc:
                    LOGGER.warning("voice_list_failed engine=system error=%s", exc)
                    return []
            return self._say_voices
