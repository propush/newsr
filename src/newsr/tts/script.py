from __future__ import annotations

from dataclasses import dataclass

from ..domain.reader import ViewMode
from .language import detect_script_language, language_code
from .text import inline_text, speech_text, spoken_sentence, split_chunks

FIRST_BODY_CHUNK_CHARS = 200


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    text: str
    language: str | None


def body_language(
    mode: ViewMode,
    text: str,
    *,
    target_language: str,
    original_language: str,
) -> str | None:
    if mode == ViewMode.ORIGINAL:
        return detect_script_language(text, original_language)
    return language_code(target_language) or detect_script_language(text, None)


def build_item_script(
    *,
    intro: str,
    intro_language: str | None,
    title: str,
    body: str,
    body_language: str | None,
    max_chars: int,
) -> list[SpeechSegment]:
    segments: list[SpeechSegment] = []
    intro_text = spoken_sentence(intro)
    if intro_text:
        segments.append(SpeechSegment(intro_text, intro_language))
    title_text = spoken_sentence(inline_text(title))
    if title_text:
        segments.append(SpeechSegment(title_text, body_language))
    for chunk in split_chunks(speech_text(body), max_chars, first_chunk_chars=FIRST_BODY_CHUNK_CHARS):
        segments.append(SpeechSegment(chunk, body_language))
    return segments
