from __future__ import annotations

from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token


@dataclass(slots=True)
class MarkdownSpan:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    href: str | None = None


@dataclass(slots=True)
class MarkdownTextBlock:
    kind: str
    spans: list[MarkdownSpan]
    level: int = 0
    indent: int = 0
    quote_depth: int = 0
    prefix: str = ""


@dataclass(slots=True)
class MarkdownCodeBlock:
    code: str
    info: str = ""
    indent: int = 0
    quote_depth: int = 0
    prefix: str = ""


MarkdownBlock = MarkdownTextBlock | MarkdownCodeBlock


class MarkdownLayoutParser:
    def __init__(self) -> None:
        self._markdown = MarkdownIt("commonmark", {"breaks": False, "html": False})

    def parse(self, text: str) -> list[MarkdownBlock]:
        blocks, _ = self._parse_blocks(self._markdown.parse(text), 0)
        return blocks

    def _parse_blocks(
        self,
        tokens: list[Token],
        index: int,
        *,
        end_type: str | None = None,
        indent: int = 0,
        quote_depth: int = 0,
    ) -> tuple[list[MarkdownBlock], int]:
        blocks: list[MarkdownBlock] = []
        while index < len(tokens):
            token = tokens[index]
            if end_type is not None and token.type == end_type:
                return blocks, index + 1

            if token.type == "heading_open":
                inline_token = self._next_inline(tokens, index + 1)
                level = int(token.tag[1:]) if token.tag.startswith("h") else 1
                blocks.append(
                    MarkdownTextBlock(
                        kind="heading",
                        spans=self._parse_inline(inline_token),
                        level=level,
                        indent=indent,
                        quote_depth=quote_depth,
                    )
                )
                index += 3
                continue

            if token.type == "paragraph_open":
                inline_token = self._next_inline(tokens, index + 1)
                blocks.append(
                    MarkdownTextBlock(
                        kind="blockquote" if quote_depth else "paragraph",
                        spans=self._parse_inline(inline_token),
                        indent=indent,
                        quote_depth=quote_depth,
                    )
                )
                index += 3
                continue

            if token.type == "inline":
                blocks.append(
                    MarkdownTextBlock(
                        kind="blockquote" if quote_depth else "paragraph",
                        spans=self._parse_inline(token),
                        indent=indent,
                        quote_depth=quote_depth,
                    )
                )
                index += 1
                continue

            if token.type == "fence":
                blocks.append(
                    MarkdownCodeBlock(
                        code=token.content.rstrip("\n"),
                        info=token.info.strip(),
                        indent=indent,
                        quote_depth=quote_depth,
                    )
                )
                index += 1
                continue

            if token.type == "bullet_list_open":
                nested, index = self._parse_list(tokens, index, indent=indent, quote_depth=quote_depth, ordered=False)
                blocks.extend(nested)
                continue

            if token.type == "ordered_list_open":
                start = self._ordered_list_start(token)
                nested, index = self._parse_list(
                    tokens,
                    index,
                    indent=indent,
                    quote_depth=quote_depth,
                    ordered=True,
                    start=start,
                )
                blocks.extend(nested)
                continue

            if token.type == "blockquote_open":
                nested, index = self._parse_blocks(
                    tokens,
                    index + 1,
                    end_type="blockquote_close",
                    indent=indent,
                    quote_depth=quote_depth + 1,
                )
                blocks.extend(nested)
                continue

            if token.type == "hr":
                blocks.append(
                    MarkdownTextBlock(
                        kind="paragraph",
                        spans=[MarkdownSpan("-----")],
                        indent=indent,
                        quote_depth=quote_depth,
                    )
                )
                index += 1
                continue

            if token.content:
                blocks.append(
                    MarkdownTextBlock(
                        kind="paragraph",
                        spans=[MarkdownSpan(token.content)],
                        indent=indent,
                        quote_depth=quote_depth,
                    )
                )
            index += 1

        return blocks, index

    def _parse_list(
        self,
        tokens: list[Token],
        index: int,
        *,
        indent: int,
        quote_depth: int,
        ordered: bool,
        start: int = 1,
    ) -> tuple[list[MarkdownBlock], int]:
        blocks: list[MarkdownBlock] = []
        close_type = "ordered_list_close" if ordered else "bullet_list_close"
        counter = start
        index += 1
        while index < len(tokens):
            token = tokens[index]
            if token.type == close_type:
                return blocks, index + 1
            if token.type != "list_item_open":
                index += 1
                continue
            item_blocks, index = self._parse_blocks(
                tokens,
                index + 1,
                end_type="list_item_close",
                indent=indent,
                quote_depth=quote_depth,
            )
            if item_blocks:
                item_blocks[0].prefix = f"{counter}. " if ordered else "• "
            blocks.extend(item_blocks)
            counter += 1
        return blocks, index

    @staticmethod
    def _ordered_list_start(token: Token) -> int:
        if token.attrs is None:
            return 1
        raw = token.attrs.get("start")
        if raw is None:
            return 1
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _next_inline(tokens: list[Token], index: int) -> Token:
        if index >= len(tokens) or tokens[index].type != "inline":
            return Token("inline", "", 0, content="")
        return tokens[index]

    def _parse_inline(self, token: Token) -> list[MarkdownSpan]:
        if not token.children:
            return [MarkdownSpan(token.content)] if token.content else []

        spans: list[MarkdownSpan] = []
        bold_depth = 0
        italic_depth = 0
        link_stack: list[str | None] = []

        for child in token.children:
            if child.type == "text" and child.content:
                spans.append(
                    MarkdownSpan(
                        child.content,
                        bold=bold_depth > 0,
                        italic=italic_depth > 0,
                        href=link_stack[-1] if link_stack else None,
                    )
                )
                continue

            if child.type in {"softbreak", "hardbreak"}:
                spans.append(MarkdownSpan("\n"))
                continue

            if child.type == "code_inline":
                spans.append(
                    MarkdownSpan(
                        child.content,
                        bold=bold_depth > 0,
                        italic=italic_depth > 0,
                        code=True,
                        href=link_stack[-1] if link_stack else None,
                    )
                )
                continue

            if child.type == "strong_open":
                bold_depth += 1
                continue

            if child.type == "strong_close":
                bold_depth = max(0, bold_depth - 1)
                continue

            if child.type == "em_open":
                italic_depth += 1
                continue

            if child.type == "em_close":
                italic_depth = max(0, italic_depth - 1)
                continue

            if child.type == "link_open":
                link_stack.append(child.attrGet("href"))
                continue

            if child.type == "link_close":
                if link_stack:
                    link_stack.pop()
                continue

            if child.type == "image":
                alt_text = child.content or "image"
                spans.append(
                    MarkdownSpan(
                        alt_text,
                        bold=bold_depth > 0,
                        italic=italic_depth > 0,
                        href=link_stack[-1] if link_stack else None,
                    )
                )
                continue

            if child.content:
                spans.append(
                    MarkdownSpan(
                        child.content,
                        bold=bold_depth > 0,
                        italic=italic_depth > 0,
                        href=link_stack[-1] if link_stack else None,
                    )
                )

        return self._merge_adjacent(spans)

    @staticmethod
    def _merge_adjacent(spans: list[MarkdownSpan]) -> list[MarkdownSpan]:
        merged: list[MarkdownSpan] = []
        for span in spans:
            if not span.text:
                continue
            if (
                merged
                and merged[-1].bold == span.bold
                and merged[-1].italic == span.italic
                and merged[-1].code == span.code
                and merged[-1].href == span.href
            ):
                merged[-1].text += span.text
                continue
            merged.append(span)
        return merged
