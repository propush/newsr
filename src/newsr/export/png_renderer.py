from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .markdown_layout import MarkdownBlock, MarkdownCodeBlock, MarkdownLayoutParser, MarkdownSpan, MarkdownTextBlock
from .models import ExportDocument


@dataclass(slots=True)
class _DrawSegment:
    text: str
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    fill: str


@dataclass(slots=True)
class _PreparedTextLine:
    segments: list[_DrawSegment]
    line_height: int
    ascent: int
    indent_px: int
    prefix: _DrawSegment | None = None
    hanging_indent_px: int = 0


@dataclass(slots=True)
class _PreparedTextBlock:
    lines: list[_PreparedTextLine]
    spacing_after: int
    quote_depth: int = 0
    quote_color: str | None = None


@dataclass(slots=True)
class _PreparedCodeBlock:
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
    prefix: _DrawSegment | None = None
    hanging_indent_px: int = 0


PreparedBlock = _PreparedTextBlock | _PreparedCodeBlock


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

        title_font = self._load_font(int(32 * scale), bold=True)
        meta_font = self._load_font(int(18 * scale))
        measure_image = Image.new("RGB", (width, minimum_height), document.theme.background)
        measure_draw = ImageDraw.Draw(measure_image)

        title_lines = self._wrap_plain_text(measure_draw, document.title, title_font, content_width)
        metadata_lines: list[str] = []
        for raw_line in (
            f"Date: {document.date_text}",
            f"Provider: {document.provider_name}",
            f"Category: {document.category}",
            f"Mode: {document.mode_label}",
            f"URL: {document.source_url}",
        ):
            metadata_lines.extend(self._wrap_plain_text(measure_draw, raw_line, meta_font, content_width))
        prepared_blocks = self._prepare_blocks(measure_draw, document, scale, content_width)

        title_line_height = self._line_height(title_font)
        meta_line_height = self._line_height(meta_font)
        header_height = (
            header_padding * 2
            + len(title_lines) * title_line_height
            + max(0, len(title_lines) - 1) * int(title_line_height * 0.25)
            + int(meta_line_height * 0.75)
            + len(metadata_lines) * meta_line_height
            + max(0, len(metadata_lines) - 1) * int(meta_line_height * 0.2)
        )
        body_height = sum(self._prepared_block_height(block) for block in prepared_blocks)
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
        y = self._draw_plain_lines(
            draw,
            title_lines,
            font=title_font,
            fill=document.theme.primary,
            x=padding_x,
            y=y,
            spacing_after=int(self._line_height(title_font) * 0.8),
        )
        y = self._draw_plain_lines(
            draw,
            metadata_lines,
            font=meta_font,
            fill=document.theme.secondary,
            x=padding_x,
            y=y,
            spacing_after=int(self._line_height(self._load_font(int(21 * scale))) * 1.0),
        )
        y = header_height + padding_y + padding_y
        for block in prepared_blocks:
            y = self._draw_prepared_block(draw, block, x=padding_x, y=y, quote_step=max(18, int(20 * scale)))

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
    ) -> _PreparedTextBlock:
        base_font_size = int(21 * scale)
        heading_sizes = {
            1: int(29 * scale),
            2: int(26 * scale),
            3: int(24 * scale),
        }
        font_size = heading_sizes.get(block.level, base_font_size) if block.kind == "heading" else base_font_size
        default_bold = block.kind == "heading"
        primary_font = self._load_font(font_size, bold=default_bold)
        prefix_font = primary_font
        prefix = self._segment_for_text(block.prefix, prefix_font, document.theme.secondary) if block.prefix else None
        prefix_width = self._segment_width(draw, prefix) if prefix is not None else 0
        content_indent_px = indent_px + (block.quote_depth * quote_step)
        quote_color = document.theme.accent if block.quote_depth else None

        tokens = self._tokenize_spans(block.spans)
        lines: list[_PreparedTextLine] = []
        current: list[_DrawSegment] = []
        current_width = 0
        line_index = 0
        max_line_width = max(1, content_width - content_indent_px)

        for text, span in tokens:
            if text == "\n":
                lines.append(
                    self._build_text_line(
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

            segment = self._segment_for_span(block, span, document, font_size)
            segment_text = text if span.code else self._normalize_space(text)
            if not segment_text:
                continue
            segment = _DrawSegment(segment_text, segment.font, segment.fill)
            line_reserved_width = prefix_width if prefix is not None else 0
            available_width = max_line_width - line_reserved_width
            segment_width = self._segment_width(draw, segment)
            if current and current_width + segment_width > max(1, available_width):
                if segment_text.isspace():
                    lines.append(
                        self._build_text_line(
                            self._rstrip_segments(current),
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
                        self._build_text_line(
                            self._rstrip_segments(current),
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

                pieces = self._split_segment_overflow(
                    draw,
                    segment,
                    max(1, available_width - current_width),
                )
                first_piece = True
                for piece in pieces:
                    piece_width = self._segment_width(draw, piece)
                    current_available = max_line_width - line_reserved_width
                    if current and current_width + piece_width > max(1, current_available):
                        lines.append(
                            self._build_text_line(
                                self._rstrip_segments(current),
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
            current_width += self._segment_width(draw, segment)

        if current or not lines:
            lines.append(
                self._build_text_line(
                    self._rstrip_segments(current),
                    line_index=line_index,
                    prefix=prefix,
                    prefix_width=prefix_width,
                    indent_px=content_indent_px,
                )
            )

        return _PreparedTextBlock(
            lines=lines,
            spacing_after=self._text_block_spacing(block, scale),
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
    ) -> _PreparedCodeBlock:
        font = self._load_font(int(21 * scale), monospace=True)
        prefix = self._segment_for_text(block.prefix, font, document.theme.secondary) if block.prefix else None
        prefix_width = self._segment_width(draw, prefix) if prefix is not None else 0
        content_indent_px = indent_px + (block.quote_depth * quote_step)
        padding_x = max(12, int(14 * scale))
        padding_y = max(10, int(12 * scale))
        usable_width = max(1, content_width - content_indent_px - prefix_width - padding_x * 2)
        lines: list[str] = []
        raw_lines = block.code.splitlines() or [""]
        for raw_line in raw_lines:
            lines.extend(self._wrap_code_line(draw, raw_line, font, usable_width))

        return _PreparedCodeBlock(
            lines=lines,
            font=font,
            fill=document.theme.foreground,
            background=document.theme.panel,
            line_height=self._line_height(font),
            indent_px=content_indent_px,
            padding_x=padding_x,
            padding_y=padding_y,
            spacing_after=max(18, int(22 * scale)),
            quote_depth=block.quote_depth,
            quote_color=document.theme.accent if block.quote_depth else None,
            prefix=prefix,
            hanging_indent_px=prefix_width,
        )

    def _draw_prepared_block(
        self,
        draw: ImageDraw.ImageDraw,
        block: PreparedBlock,
        *,
        x: int,
        y: int,
        quote_step: int,
    ) -> int:
        if isinstance(block, _PreparedCodeBlock):
            return self._draw_code_block(draw, block, x=x, y=y, quote_step=quote_step)
        return self._draw_text_block(draw, block, x=x, y=y, quote_step=quote_step)

    def _draw_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        block: _PreparedTextBlock,
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
                    (x + line.indent_px, baseline_y - self._font_ascent(line.prefix.font)),
                    line.prefix.text,
                    font=line.prefix.font,
                    fill=line.prefix.fill,
                )
            cursor_x = line_x
            for segment in line.segments:
                draw.text(
                    (cursor_x, baseline_y - self._font_ascent(segment.font)),
                    segment.text,
                    font=segment.font,
                    fill=segment.fill,
                )
                cursor_x += self._segment_width(draw, segment)
            y += line.line_height
            if line is not block.lines[-1]:
                y += int(line.line_height * 0.2)
        if block.quote_depth and block.quote_color is not None:
            quote_x = x + (block.lines[0].indent_px - (block.quote_depth * quote_step)) + max(6, quote_step // 3)
            draw.line((quote_x, start_y, quote_x, y), fill=block.quote_color, width=max(2, quote_step // 6))
        return y + block.spacing_after

    def _draw_code_block(
        self,
        draw: ImageDraw.ImageDraw,
        block: _PreparedCodeBlock,
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
        right = left + self._code_block_width(draw, block)
        bottom = y + self._prepared_block_height(block) - block.spacing_after
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

    def _draw_plain_lines(
        self,
        draw: ImageDraw.ImageDraw,
        lines: list[str],
        *,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        fill: str,
        x: int,
        y: int,
        spacing_after: int,
    ) -> int:
        line_height = self._line_height(font)
        for index, line in enumerate(lines):
            draw.text((x, y), line, font=font, fill=fill)
            y += line_height
            if index < len(lines) - 1:
                y += int(line_height * 0.2)
        return y + spacing_after

    def _build_text_line(
        self,
        segments: list[_DrawSegment],
        *,
        line_index: int,
        prefix: _DrawSegment | None,
        prefix_width: int,
        indent_px: int,
    ) -> _PreparedTextLine:
        fonts = [segment.font for segment in segments]
        if prefix is not None:
            fonts.append(prefix.font)
        if not fonts:
            fonts = [self._load_font(24)]
        ascent = max(self._font_ascent(font) for font in fonts)
        descent = max(self._font_descent(font) for font in fonts)
        line_height = max(1, ascent + descent + 6)
        return _PreparedTextLine(
            segments=self._merge_segments(segments),
            line_height=line_height,
            ascent=ascent,
            indent_px=indent_px,
            prefix=prefix if line_index == 0 else None,
            hanging_indent_px=prefix_width if prefix is not None else 0,
        )

    def _text_block_spacing(self, block: MarkdownTextBlock, scale: float) -> int:
        if block.kind == "heading":
            if block.level == 1:
                return max(20, int(24 * scale))
            return max(16, int(20 * scale))
        return max(12, int(16 * scale))

    def _tokenize_spans(self, spans: list[MarkdownSpan]) -> list[tuple[str, MarkdownSpan]]:
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

    def _segment_for_span(
        self,
        block: MarkdownTextBlock,
        span: MarkdownSpan,
        document: ExportDocument,
        font_size: int,
    ) -> _DrawSegment:
        font = self._load_font(
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
        return _DrawSegment(span.text, font, fill)

    @staticmethod
    def _segment_for_text(
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        fill: str,
    ) -> _DrawSegment:
        return _DrawSegment(text, font, fill)

    @staticmethod
    def _normalize_space(text: str) -> str:
        return " " if text.isspace() else text

    @staticmethod
    def _rstrip_segments(segments: list[_DrawSegment]) -> list[_DrawSegment]:
        trimmed = [_DrawSegment(segment.text, segment.font, segment.fill) for segment in segments]
        while trimmed and trimmed[-1].text.isspace():
            trimmed.pop()
        if trimmed:
            trimmed[-1].text = trimmed[-1].text.rstrip()
            if not trimmed[-1].text:
                trimmed.pop()
        return trimmed

    def _split_segment_overflow(
        self,
        draw: ImageDraw.ImageDraw,
        segment: _DrawSegment,
        available_width: int,
    ) -> list[_DrawSegment]:
        if self._segment_width(draw, segment) <= max(1, available_width):
            return [segment]
        pieces: list[_DrawSegment] = []
        current = ""
        for char in segment.text:
            candidate = f"{current}{char}"
            candidate_segment = _DrawSegment(candidate, segment.font, segment.fill)
            if current and self._segment_width(draw, candidate_segment) > max(1, available_width):
                pieces.append(_DrawSegment(current, segment.font, segment.fill))
                current = char
                available_width = self._segment_width(draw, _DrawSegment(char, segment.font, segment.fill))
                continue
            current = candidate
        if current:
            pieces.append(_DrawSegment(current, segment.font, segment.fill))
        return pieces

    def _wrap_plain_text(
        self,
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
            lines.extend(self._wrap_plain_line(draw, raw_line, font, max_width))
        return lines or [""]

    def _wrap_plain_line(
        self,
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
            if self._text_width(draw, candidate, font) <= max_width:
                current = candidate
                continue
            lines.extend(self._split_plain_overflow(draw, current, font, max_width))
            current = word
        lines.extend(self._split_plain_overflow(draw, current, font, max_width))
        return lines

    def _wrap_code_line(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        if not text:
            return [""]
        return self._split_plain_overflow(draw, text, font, max_width)

    def _split_plain_overflow(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
    ) -> list[str]:
        if self._text_width(draw, text, font) <= max_width:
            return [text]
        pieces: list[str] = []
        current = ""
        for char in text:
            candidate = f"{current}{char}"
            if current and self._text_width(draw, candidate, font) > max_width:
                pieces.append(current)
                current = char
                continue
            current = candidate
        if current:
            pieces.append(current)
        return pieces

    def _prepared_block_height(self, block: PreparedBlock) -> int:
        if isinstance(block, _PreparedCodeBlock):
            line_gap = int(block.line_height * 0.15)
            body_height = len(block.lines) * block.line_height + max(0, len(block.lines) - 1) * line_gap
            return block.padding_y * 2 + body_height + block.spacing_after
        return (
            sum(line.line_height for line in block.lines)
            + sum(int(line.line_height * 0.2) for line in block.lines[:-1])
            + block.spacing_after
        )

    def _code_block_width(self, draw: ImageDraw.ImageDraw, block: _PreparedCodeBlock) -> int:
        longest = max((self._text_width(draw, line, block.font) for line in block.lines), default=0)
        return longest + (block.padding_x * 2)

    @staticmethod
    def _merge_segments(segments: list[_DrawSegment]) -> list[_DrawSegment]:
        merged: list[_DrawSegment] = []
        for segment in segments:
            if not segment.text:
                continue
            if merged and merged[-1].font == segment.font and merged[-1].fill == segment.fill:
                merged[-1].text += segment.text
                continue
            merged.append(segment)
        return merged

    def _dimensions_for_quality(self, quality: str) -> tuple[int, int]:
        if quality not in self._QUALITY_DIMENSIONS:
            raise ValueError(f"unsupported image quality: {quality}")
        return self._QUALITY_DIMENSIONS[quality]

    @staticmethod
    def _line_height(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
        return max(1, PillowPngRenderer._font_ascent(font) + PillowPngRenderer._font_descent(font) + 6)

    @staticmethod
    def _font_ascent(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
        if hasattr(font, "getmetrics"):
            ascent, _ = font.getmetrics()
            return max(1, ascent)
        bbox = font.getbbox("H")
        return max(1, bbox[3] - bbox[1])

    @staticmethod
    def _font_descent(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
        if hasattr(font, "getmetrics"):
            _, descent = font.getmetrics()
            return max(0, descent)
        bbox = font.getbbox("g")
        return max(0, bbox[3])

    def _segment_width(self, draw: ImageDraw.ImageDraw, segment: _DrawSegment | None) -> int:
        if segment is None or not segment.text:
            return 0
        return self._text_width(draw, segment.text, segment.font)

    @staticmethod
    def _text_width(
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> int:
        if not text:
            return 0
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        return right - left

    def _load_font(
        self,
        size: int,
        *,
        bold: bool = False,
        italic: bool = False,
        monospace: bool = False,
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for path in self._font_candidates(bold=bold, italic=italic, monospace=monospace):
            if not path.exists():
                continue
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _font_candidates(*, bold: bool, italic: bool, monospace: bool) -> list[Path]:
        if monospace:
            return [
                Path("/System/Library/Fonts/Menlo.ttc"),
                Path("/System/Library/Fonts/SFNSMono.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
                Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"),
                Path("C:/Windows/Fonts/consola.ttf"),
            ]
        if bold and italic:
            return [
                Path("/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"),
                Path("C:/Windows/Fonts/arialbi.ttf"),
            ]
        if bold:
            return [
                Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
                Path("/System/Library/Fonts/Helvetica.ttc"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                Path("C:/Windows/Fonts/arialbd.ttf"),
            ]
        if italic:
            return [
                Path("/System/Library/Fonts/Supplemental/Arial Italic.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
                Path("C:/Windows/Fonts/ariali.ttf"),
            ]
        return [
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
        ]
