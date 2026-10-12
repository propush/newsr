from __future__ import annotations

from newsr.tts.text import inline_text, speech_text, split_chunks


def test_speech_text_strips_markdown_code_and_urls() -> None:
    markdown = (
        "# Heading\n\n"
        "Some **bold** text with [a link](https://example.com) and https://example.com/raw\n"
        "continued line\n\n"
        "- first item\n- second item!\n\n"
        "```\nprint('skip me')\n```\n\n"
        "---\n"
    )

    assert speech_text(markdown) == (
        "Heading.\n\n"
        "Some bold text with a link and continued line.\n\n"
        "first item.\n\n"
        "second item!"
    )


def test_inline_text_removes_markup_characters() -> None:
    assert inline_text("**Breaking**: `news` _today_ https://x.y") == "Breaking: news today"


def test_split_chunks_keeps_paragraphs_together_until_the_limit() -> None:
    text = "One.\n\nTwo.\n\nThree is longer."

    assert split_chunks(text, 16) == ["One.\n\nTwo.", "Three is longer."]


def test_split_chunks_splits_long_paragraphs_by_sentence_then_word() -> None:
    text = "First sentence here. Second one! " + "word " * 10

    chunks = split_chunks(text.strip(), 25)

    assert chunks[0] == "First sentence here."
    assert chunks[1] == "Second one!"
    assert all(len(chunk) <= 25 for chunk in chunks)
    assert " ".join(chunks[2:]).split() == ["word"] * 10


def test_split_chunks_breaks_words_longer_than_the_limit() -> None:
    assert split_chunks("abcdefghij", 4) == ["abcd", "efgh", "ij"]
