from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from .markdown_layout import (
    MarkdownBlock,
    MarkdownCodeBlock,
    MarkdownLayoutParser,
    MarkdownSpan,
    MarkdownTextBlock,
)
from .models import ExportDocument
from .png_blocks import (
    DrawSegment,
    PreparedBlock,
    PreparedCodeBlock,
    PreparedTextBlock,
    PreparedTextLine,
    prepared_block_height,
)
from .png_draw import draw_plain_lines, draw_prepared_block
from .png_fonts import font_line_height, load_font
from .png_text import (
    build_text_line,
    measure_segment,
    normalize_space,
    rstrip_segments,
    segment_for_span,
    segment_for_text,
    split_segment_overflow,
    text_block_spacing,
    tokenize_spans,
    wrap_code_line,
    wrap_plain_text,
)


class PillowPngRenderer:
    _QUALITY_DIMENSIONS = {
        "hd": (720, 1280),
        "fhd": (1080, 1920),
    }

    def __init__(self) -> None:
        self._markdown_parser = MarkdownLayoutParser()

    def render(self, document: ExportDocument, quality: str) -> bytes:
        width, minimum_height = self._dimensions_for_quality(quality)
        scale = width / 720
        padding_x = max(48, int(56 * scale))
        padding_y = max(40, int(48 * scale))
        header_padding = max(24, int(28 * scale))
        content_width = width - (padding_x * 2)

        title_font = load_font(int(32 * scale), bold=True)
        meta_font = load_font(int(18 * scale))
        measure_image = Image.new("RGB", (width, minimum_height), document.theme.background)
        measure_draw = ImageDraw.Draw(measure_image)

        title_lines = wrap_plain_text(measure_draw, document.title, title_font, content_width)
        metadata_lines: list[str] = []
        for raw_line in (
            f"Date: {document.date_text}",
            f"Provider: {document.provider_name}",
            f"Category: {document.category}",
            f"Mode: {document.mode_label}",
            f"URL: {document.source_url}",
        ):
            metadata_lines.extend(wrap_plain_text(measure_draw, raw_line, meta_font, content_width))
        prepared_blocks = self._prepare_blocks(measure_draw, document, scale, content_width)

        title_line_height = font_line_height(title_font)
        meta_line_height = font_line_height(meta_font)
        header_height = (
            header_padding * 2
            + len(title_lines) * title_line_height
            + max(0, len(title_lines) - 1) * int(title_line_height * 0.25)
            + int(meta_line_height * 0.75)
            + len(metadata_lines) * meta_line_height
            + max(0, len(metadata_lines) - 1) * int(meta_line_height * 0.2)
        )
        body_height = sum(prepared_block_height(block) for block in prepared_blocks)
        content_height = padding_y + header_height + padding_y
        total_height = max(minimum_height, content_height + body_height)

        image = Image.new("RGB", (width, total_height), document.theme.background)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, header_height + padding_y), fill=document.theme.panel)
        draw.line(
            (padding_x, header_height + padding_y, width - padding_x, header_height + padding_y),
            fill=document.theme.accent,
            width=max(2, int(3 * scale)),
        )

        y = padding_y
        y = draw_plain_lines(
            draw,
            title_lines,
            font=title_font,
            fill=document.theme.primary,
            x=padding_x,
            y=y,
            spacing_after=int(font_line_height(title_font) * 0.8),
        )
        y = draw_plain_lines(
            draw,
            metadata_lines,
            font=meta_font,
            fill=document.theme.secondary,
            x=padding_x,
            y=y,
            spacing_after=int(font_line_height(load_font(int(21 * scale))) * 1.0),
        )
        y = header_height + padding_y + padding_y
        for block in prepared_blocks:
            y = draw_prepared_block(draw, block, x=padding_x, y=y, quote_step=max(18, int(20 * scale)))

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _prepare_blocks(
        self,
        draw: ImageDraw.ImageDraw,
        document: ExportDocument,
        scale: float,
        content_width: int,
    ) -> list[PreparedBlock]:
        blocks = self._markdown_parser.parse(document.body)
        if not blocks:
            blocks = [MarkdownTextBlock(kind="paragraph", spans=[MarkdownSpan(document.body)])]
        return [self._prepare_block(draw, block, document, scale, content_width) for block in blocks]

    def _prepare_block(
        self,
        draw: ImageDraw.ImageDraw,
        block: MarkdownBlock,
        document: ExportDocument,
        scale: float,
        content_width: int,
    ) -> PreparedBlock:
        list_indent = max(24, int(28 * scale))
        quote_step = max(18, int(20 * scale))
        indent_px = block.indent * list_indent
        if isinstance(block, MarkdownCodeBlock):
            return self._prepare_code_block(
                draw,
                block,
                document,
                scale,
                content_width,
                indent_px=indent_px,
                quote_step=quote_step,
            )
        return self._prepare_text_block(
            draw,
            block,
            document,
            scale,
            content_width,
            indent_px=indent_px,
            quote_step=quote_step,
        )

    def _prepare_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        block: MarkdownTextBlock,
        document: ExportDocument,
        scale: float,
        content_width: int,
        *,
        indent_px: int,
        quote_step: int,
    ) -> PreparedTextBlock:
        base_font_size = int(21 * scale)
        heading_sizes = {
            1: int(29 * scale),
            2: int(26 * scale),
            3: int(24 * scale),
        }
        font_size = heading_sizes.get(block.level, base_font_size) if block.kind == "heading" else base_font_size
        default_bold = block.kind == "heading"
        primary_font = load_font(font_size, bold=default_bold)
        prefix_font = primary_font
        prefix = segment_for_text(block.prefix, prefix_font, document.theme.secondary) if block.prefix else None
        prefix_width = measure_segment(draw, prefix) if prefix is not None else 0
        content_indent_px = indent_px + (block.quote_depth * quote_step)
        quote_color = document.theme.accent if block.quote_depth else None

        tokens = tokenize_spans(block.spans)
        lines: list[PreparedTextLine] = []
        current: list[DrawSegment] = []
        current_width = 0
        line_index = 0
        max_line_width = max(1, content_width - content_indent_px)

        for text, span in tokens:
            if text == "\n":
                lines.append(
                    build_text_line(
                        current,
                        line_index=line_index,
                        prefix=prefix,
                        prefix_width=prefix_width,
                        indent_px=content_indent_px,
                    )
                )
                current = []
                current_width = 0
                line_index += 1
                continue

            if text.isspace() and not current:
                continue

            segment = segment_for_span(block, span, document, font_size)
            segment_text = text if span.code else normalize_space(text)
            if not segment_text:
                continue
            segment = DrawSegment(segment_text, segment.font, segment.fill)
            line_reserved_width = prefix_width if prefix is not None else 0
            available_width = max_line_width - line_reserved_width
            segment_width = measure_segment(draw, segment)
            if current and current_width + segment_width > max(1, available_width):
                if segment_text.isspace():
                    lines.append(
                        build_text_line(
                            rstrip_segments(current),
                            line_index=line_index,
                            prefix=prefix,
                            prefix_width=prefix_width,
                            indent_px=content_indent_px,
                        )
                    )
                    current = []
                    current_width = 0
                    line_index += 1
                    continue

                if segment_width <= max(1, available_width):
                    lines.append(
                        build_text_line(
                            rstrip_segments(current),
                            line_index=line_index,
                            prefix=prefix,
                            prefix_width=prefix_width,
                            indent_px=content_indent_px,
                        )
                    )
                    current = [segment]
                    current_width = segment_width
                    line_index += 1
                    continue

                pieces = split_segment_overflow(
                    draw,
                    segment,
                    max(1, available_width - current_width),
                )
                first_piece = True
                for piece in pieces:
                    piece_width = measure_segment(draw, piece)
                    current_available = max_line_width - line_reserved_width
                    if current and current_width + piece_width > max(1, current_available):
                        lines.append(
                            build_text_line(
                                rstrip_segments(current),
                                line_index=line_index,
                                prefix=prefix,
                                prefix_width=prefix_width,
                                indent_px=content_indent_px,
                            )
                        )
                        current = []
                        current_width = 0
                        line_index += 1
                        current_available = max_line_width - line_reserved_width
                    if piece.text.isspace() and not current:
                        continue
                    current.append(piece)
                    current_width += piece_width
                    if first_piece:
                        first_piece = False
                continue

            current.append(segment)
            current_width += measure_segment(draw, segment)

        if current or not lines:
            lines.append(
                build_text_line(
                    rstrip_segments(current),
                    line_index=line_index,
                    prefix=prefix,
                    prefix_width=prefix_width,
                    indent_px=content_indent_px,
                )
            )

        return PreparedTextBlock(
            lines=lines,
            spacing_after=text_block_spacing(block, scale),
            quote_depth=block.quote_depth,
            quote_color=quote_color,
        )

    def _prepare_code_block(
        self,
        draw: ImageDraw.ImageDraw,
        block: MarkdownCodeBlock,
        document: ExportDocument,
        scale: float,
        content_width: int,
        *,
        indent_px: int,
        quote_step: int,
    ) -> PreparedCodeBlock:
        font = load_font(int(21 * scale), monospace=True)
        prefix = segment_for_text(block.prefix, font, document.theme.secondary) if block.prefix else None
        prefix_width = measure_segment(draw, prefix) if prefix is not None else 0
        content_indent_px = indent_px + (block.quote_depth * quote_step)
        padding_x = max(12, int(14 * scale))
        padding_y = max(10, int(12 * scale))
        usable_width = max(1, content_width - content_indent_px - prefix_width - padding_x * 2)
        lines: list[str] = []
        raw_lines = block.code.splitlines() or [""]
        for raw_line in raw_lines:
            lines.extend(wrap_code_line(draw, raw_line, font, usable_width))

        return PreparedCodeBlock(
            lines=lines,
            font=font,
            fill=document.theme.foreground,
            background=document.theme.panel,
            line_height=font_line_height(font),
            indent_px=content_indent_px,
            padding_x=padding_x,
            padding_y=padding_y,
            spacing_after=max(18, int(22 * scale)),
            quote_depth=block.quote_depth,
            quote_color=document.theme.accent if block.quote_depth else None,
            prefix=prefix,
            hanging_indent_px=prefix_width,
        )

    def _dimensions_for_quality(self, quality: str) -> tuple[int, int]:
        if quality not in self._QUALITY_DIMENSIONS:
            raise ValueError(f"unsupported image quality: {quality}")
        return self._QUALITY_DIMENSIONS[quality]
