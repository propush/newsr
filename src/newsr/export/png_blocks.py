from __future__ import annotations

from dataclasses import dataclass

from PIL import ImageFont


@dataclass(slots=True)
class DrawSegment:
    text: str
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    fill: str


@dataclass(slots=True)
class PreparedTextLine:
    segments: list[DrawSegment]
    line_height: int
    ascent: int
    indent_px: int
    prefix: DrawSegment | None = None
    hanging_indent_px: int = 0


@dataclass(slots=True)
class PreparedTextBlock:
    lines: list[PreparedTextLine]
    spacing_after: int
    quote_depth: int = 0
    quote_color: str | None = None


@dataclass(slots=True)
class PreparedCodeBlock:
    lines: list[str]
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    fill: str
    background: str
    line_height: int
    indent_px: int
    padding_x: int
    padding_y: int
    spacing_after: int
    quote_depth: int = 0
    quote_color: str | None = None
    prefix: DrawSegment | None = None
    hanging_indent_px: int = 0


PreparedBlock = PreparedTextBlock | PreparedCodeBlock


def prepared_block_height(block: PreparedBlock) -> int:
    if isinstance(block, PreparedCodeBlock):
        line_gap = int(block.line_height * 0.15)
        body_height = len(block.lines) * block.line_height + max(0, len(block.lines) - 1) * line_gap
        return block.padding_y * 2 + body_height + block.spacing_after
    return (
        sum(line.line_height for line in block.lines)
        + sum(int(line.line_height * 0.2) for line in block.lines[:-1])
        + block.spacing_after
    )
