from __future__ import annotations

import re

from ..export.markdown_layout import MarkdownCodeBlock, MarkdownLayoutParser

_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?…。！？])\s+")
_TERMINAL_PUNCTUATION = tuple(".!?…:;。！？")
_WHITESPACE = re.compile(r"\s+")
_INLINE_MARKUP = re.compile(r"[*_`#]+")


def speech_text(markdown: str) -> str:
    paragraphs: list[str] = []
    for block in MarkdownLayoutParser().parse(markdown):
        if isinstance(block, MarkdownCodeBlock):
            continue
        text = "".join(span.text for span in block.spans)
        text = _WHITESPACE.sub(" ", _URL_PATTERN.sub("", text)).strip()
        if not any(character.isalnum() for character in text):
            continue
        paragraphs.append(spoken_sentence(text))
    return "\n\n".join(paragraphs)


def inline_text(text: str) -> str:
    return _WHITESPACE.sub(" ", _INLINE_MARKUP.sub("", _URL_PATTERN.sub("", text))).strip()


def spoken_sentence(text: str) -> str:
    text = text.strip()
    if not text or text.endswith(_TERMINAL_PUNCTUATION):
        return text
    return f"{text}."


def split_chunks(text: str, max_chars: int, *, first_chunk_chars: int | None = None) -> list[str]:
    """Split speech text into chunks of at most `max_chars`.

    With `first_chunk_chars`, the first chunk stays near that size and each following chunk may be
    twice as long as the previous one, so playback can start before long text is synthesized.
    """
    pieces: list[tuple[int, str]] = []
    for paragraph_index, paragraph in enumerate(text.split("\n\n")):
        for sentence in _SENTENCE_BREAK.split(paragraph.strip()):
            pieces.extend((paragraph_index, part) for part in _split_long(sentence.strip(), max_chars))
    limit = min(max_chars, first_chunk_chars or max_chars)
    chunks: list[str] = []
    current = ""
    current_paragraph = -1
    for paragraph_index, piece in pieces:
        separator = " " if paragraph_index == current_paragraph else "\n\n"
        candidate = f"{current}{separator}{piece}" if current else piece
        if not current or len(candidate) <= limit:
            current = candidate
            current_paragraph = paragraph_index
            continue
        chunks.append(current)
        limit = min(max_chars, limit * 2)
        current = piece
        current_paragraph = paragraph_index
    if current:
        chunks.append(current)
    return chunks


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text] if text else []
    parts: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > max_chars:
            if current:
                parts.append(current)
                current = ""
            parts.append(word[:max_chars])
            word = word[max_chars:]
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            parts.append(current)
            current = word
    if current:
        parts.append(current)
    return parts
