from __future__ import annotations

import re

from PIL import ImageDraw, ImageFont

from .markdown_layout import MarkdownSpan, MarkdownTextBlock
from .models import ExportDocument
from .png_blocks import DrawSegment, PreparedTextLine
from .png_fonts import font_ascent, font_descent, load_font, text_width


def build_text_line(
    segments: list[DrawSegment],
    *,
    line_index: int,
    prefix: DrawSegment | None,
    prefix_width: int,
    indent_px: int,
) -> PreparedTextLine:
    fonts = [segment.font for segment in segments]
    if prefix is not None:
        fonts.append(prefix.font)
    if not fonts:
        fonts = [load_font(24)]
    ascent = max(font_ascent(font) for font in fonts)
    descent = max(font_descent(font) for font in fonts)
    line_height = max(1, ascent + descent + 6)
    return PreparedTextLine(
        segments=merge_segments(segments),
        line_height=line_height,
        ascent=ascent,
        indent_px=indent_px,
        prefix=prefix if line_index == 0 else None,
        hanging_indent_px=prefix_width if prefix is not None else 0,
    )


def text_block_spacing(block: MarkdownTextBlock, scale: float) -> int:
    if block.kind == "heading":
        if block.level == 1:
            return max(20, int(24 * scale))
        return max(16, int(20 * scale))
    return max(12, int(16 * scale))


def tokenize_spans(spans: list[MarkdownSpan]) -> list[tuple[str, MarkdownSpan]]:
    tokens: list[tuple[str, MarkdownSpan]] = []
    for span in spans:
        if not span.text:
            continue
        pieces = re.findall(r"\n|[^\S\n]+|\S+", span.text)
        if not pieces:
            pieces = [span.text]
        for piece in pieces:
            tokens.append((piece, span))
    return tokens


def segment_for_span(
    block: MarkdownTextBlock,
    span: MarkdownSpan,
    document: ExportDocument,
    font_size: int,
) -> DrawSegment:
    font = load_font(
        font_size if not span.code else max(12, font_size - 2),
        bold=block.kind == "heading" or span.bold,
        italic=span.italic and not span.code,
        monospace=span.code,
    )
    if span.href:
        fill = document.theme.accent
    elif span.code:
        fill = document.theme.primary
    elif block.kind == "heading":
        fill = document.theme.primary
    else:
        fill = document.theme.foreground
    return DrawSegment(span.text, font, fill)


def segment_for_text(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
) -> DrawSegment:
    return DrawSegment(text, font, fill)


def normalize_space(text: str) -> str:
    return " " if text.isspace() else text


def rstrip_segments(segments: list[DrawSegment]) -> list[DrawSegment]:
    trimmed = [DrawSegment(segment.text, segment.font, segment.fill) for segment in segments]
    while trimmed and trimmed[-1].text.isspace():
        trimmed.pop()
    if trimmed:
        trimmed[-1].text = trimmed[-1].text.rstrip()
        if not trimmed[-1].text:
            trimmed.pop()
    return trimmed


def split_segment_overflow(
    draw: ImageDraw.ImageDraw,
    segment: DrawSegment,
    available_width: int,
) -> list[DrawSegment]:
    if measure_segment(draw, segment) <= max(1, available_width):
        return [segment]
    pieces: list[DrawSegment] = []
    current = ""
    for char in segment.text:
        candidate = f"{current}{char}"
        candidate_segment = DrawSegment(candidate, segment.font, segment.fill)
        if current and measure_segment(draw, candidate_segment) > max(1, available_width):
            pieces.append(DrawSegment(current, segment.font, segment.fill))
            current = char
            available_width = measure_segment(draw, DrawSegment(char, segment.font, segment.fill))
            continue
        current = candidate
    if current:
        pieces.append(DrawSegment(current, segment.font, segment.fill))
    return pieces


def merge_segments(segments: list[DrawSegment]) -> list[DrawSegment]:
    merged: list[DrawSegment] = []
    for segment in segments:
        if not segment.text:
            continue
        if merged and merged[-1].font == segment.font and merged[-1].fill == segment.fill:
            merged[-1].text += segment.text
            continue
        merged.append(segment)
    return merged


def measure_segment(draw: ImageDraw.ImageDraw, segment: DrawSegment | None) -> int:
    if segment is None or not segment.text:
        return 0
    return text_width(draw, segment.text, segment.font)


def wrap_plain_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            lines.append("")
            continue
        lines.extend(wrap_plain_line(draw, raw_line, font, max_width))
    return lines or [""]


def wrap_plain_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        lines.extend(split_plain_overflow(draw, current, font, max_width))
        current = word
    lines.extend(split_plain_overflow(draw, current, font, max_width))
    return lines


def wrap_code_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    if not text:
        return [""]
    return split_plain_overflow(draw, text, font, max_width)


def split_plain_overflow(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    if text_width(draw, text, font) <= max_width:
        return [text]
    pieces: list[str] = []
    current = ""
    for char in text:
        candidate = f"{current}{char}"
        if current and text_width(draw, candidate, font) > max_width:
            pieces.append(current)
            current = char
            continue
        current = candidate
    if current:
        pieces.append(current)
    return pieces
