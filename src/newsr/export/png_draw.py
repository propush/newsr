from __future__ import annotations

from PIL import ImageDraw, ImageFont

from .png_blocks import PreparedBlock, PreparedCodeBlock, PreparedTextBlock, prepared_block_height
from .png_fonts import font_ascent, font_line_height, text_width
from .png_text import measure_segment


def draw_prepared_block(
    draw: ImageDraw.ImageDraw,
    block: PreparedBlock,
    *,
    x: int,
    y: int,
    quote_step: int,
) -> int:
    if isinstance(block, PreparedCodeBlock):
        return draw_code_block(draw, block, x=x, y=y, quote_step=quote_step)
    return draw_text_block(draw, block, x=x, y=y, quote_step=quote_step)


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    block: PreparedTextBlock,
    *,
    x: int,
    y: int,
    quote_step: int,
) -> int:
    start_y = y
    for line in block.lines:
        line_x = x + line.indent_px + line.hanging_indent_px
        baseline_y = y + line.ascent
        if line.prefix is not None:
            draw.text(
                (x + line.indent_px, baseline_y - font_ascent(line.prefix.font)),
                line.prefix.text,
                font=line.prefix.font,
                fill=line.prefix.fill,
            )
        cursor_x = line_x
        for segment in line.segments:
            draw.text(
                (cursor_x, baseline_y - font_ascent(segment.font)),
                segment.text,
                font=segment.font,
                fill=segment.fill,
            )
            cursor_x += measure_segment(draw, segment)
        y += line.line_height
        if line is not block.lines[-1]:
            y += int(line.line_height * 0.2)
    if block.quote_depth and block.quote_color is not None:
        quote_x = x + (block.lines[0].indent_px - (block.quote_depth * quote_step)) + max(6, quote_step // 3)
        draw.line((quote_x, start_y, quote_x, y), fill=block.quote_color, width=max(2, quote_step // 6))
    return y + block.spacing_after


def draw_code_block(
    draw: ImageDraw.ImageDraw,
    block: PreparedCodeBlock,
    *,
    x: int,
    y: int,
    quote_step: int,
) -> int:
    start_y = y
    left = x + block.indent_px + block.hanging_indent_px
    if block.prefix is not None:
        draw.text((x + block.indent_px, y + block.padding_y), block.prefix.text, font=block.prefix.font, fill=block.prefix.fill)
    top = y
    right = left + code_block_width(draw, block)
    bottom = y + prepared_block_height(block) - block.spacing_after
    draw.rectangle((left, top, right, bottom), fill=block.background)
    text_y = y + block.padding_y
    for line in block.lines:
        draw.text((left + block.padding_x, text_y), line, font=block.font, fill=block.fill)
        text_y += block.line_height
        if line is not block.lines[-1]:
            text_y += int(block.line_height * 0.15)
    if block.quote_depth and block.quote_color is not None:
        quote_x = x + (block.indent_px - (block.quote_depth * quote_step)) + max(6, quote_step // 3)
        draw.line((quote_x, start_y, quote_x, bottom), fill=block.quote_color, width=max(2, quote_step // 6))
    return bottom + block.spacing_after


def draw_plain_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    x: int,
    y: int,
    spacing_after: int,
) -> int:
    line_height = font_line_height(font)
    for index, line in enumerate(lines):
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
        if index < len(lines) - 1:
            y += int(line_height * 0.2)
    return y + spacing_after


def code_block_width(draw: ImageDraw.ImageDraw, block: PreparedCodeBlock) -> int:
    longest = max((text_width(draw, line, block.font) for line in block.lines), default=0)
    return longest + (block.padding_x * 2)
