from __future__ import annotations

from newsr.export.markdown_layout import MarkdownCodeBlock, MarkdownLayoutParser, MarkdownTextBlock


def test_markdown_layout_parser_supports_common_markdown_subset() -> None:
    parser = MarkdownLayoutParser()

    blocks = parser.parse(
        "# Heading\n\n"
        "Paragraph with **bold** text, *italic* text, `code`, and [a link](https://example.com).\n\n"
        "- first item\n"
        "- second item\n\n"
        "1. ordered\n"
        "2. list\n\n"
        "```python\n"
        "print('hello')\n"
        "```\n\n"
        "> quoted line"
    )

    assert [type(block).__name__ for block in blocks] == [
        "MarkdownTextBlock",
        "MarkdownTextBlock",
        "MarkdownTextBlock",
        "MarkdownTextBlock",
        "MarkdownTextBlock",
        "MarkdownTextBlock",
        "MarkdownCodeBlock",
        "MarkdownTextBlock",
    ]

    heading = blocks[0]
    assert isinstance(heading, MarkdownTextBlock)
    assert heading.kind == "heading"
    assert heading.level == 1
    assert "".join(span.text for span in heading.spans) == "Heading"

    paragraph = blocks[1]
    assert isinstance(paragraph, MarkdownTextBlock)
    assert paragraph.kind == "paragraph"
    assert not any(marker in "".join(span.text for span in paragraph.spans) for marker in ("**", "*", "`", "[", "]", "(", ")"))
    assert any(span.bold and span.text == "bold" for span in paragraph.spans)
    assert any(span.italic and span.text == "italic" for span in paragraph.spans)
    assert any(span.code and span.text == "code" for span in paragraph.spans)
    assert any(span.href == "https://example.com" and span.text == "a link" for span in paragraph.spans)

    first_bullet = blocks[2]
    assert isinstance(first_bullet, MarkdownTextBlock)
    assert first_bullet.prefix == "• "

    first_ordered = blocks[4]
    assert isinstance(first_ordered, MarkdownTextBlock)
    assert first_ordered.prefix == "1. "

    second_ordered = blocks[5]
    assert isinstance(second_ordered, MarkdownTextBlock)
    assert second_ordered.prefix == "2. "

    code_block = blocks[6]
    assert isinstance(code_block, MarkdownCodeBlock)
    assert code_block.code == "print('hello')"

    quote = blocks[7]
    assert isinstance(quote, MarkdownTextBlock)
    assert quote.kind == "blockquote"
    assert quote.quote_depth == 1


def test_markdown_layout_parser_falls_back_to_plain_text_for_unsupported_tokens() -> None:
    parser = MarkdownLayoutParser()

    blocks = parser.parse("| a | b |\n| - | - |\n| 1 | 2 |")

    assert blocks
    assert isinstance(blocks[0], MarkdownTextBlock)
    assert "a" in "".join(span.text for span in blocks[0].spans)
