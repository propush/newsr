from __future__ import annotations

import array

from newsr.tts.player import (
    LEADING_SILENCE_SECONDS,
    SAMPLE_RATE,
    TRAILING_SILENCE_SECONDS,
    trim_silence,
)


def stereo_pcm(*segments: tuple[float, int]) -> bytes:
    samples = array.array("h")
    for seconds, value in segments:
        samples.extend([value] * (int(seconds * SAMPLE_RATE) * 2))
    return samples.tobytes()


def frames(pcm: bytes) -> int:
    return len(pcm) // 4


def test_trim_silence_shortens_leading_and_trailing_silence() -> None:
    pcm = stereo_pcm((0.25, 0), (0.5, 4000), (1.0, 10))

    trimmed = trim_silence(pcm)

    expected = int(LEADING_SILENCE_SECONDS * SAMPLE_RATE) + int(0.5 * SAMPLE_RATE) + int(
        TRAILING_SILENCE_SECONDS * SAMPLE_RATE
    )
    assert frames(trimmed) == expected


def test_trim_silence_keeps_short_padding_and_silent_clips() -> None:
    tight = stereo_pcm((0.02, 0), (0.5, 4000), (0.1, 0))
    silent = stereo_pcm((0.5, 0))

    assert trim_silence(tight) == tight
    assert trim_silence(silent) == silent
