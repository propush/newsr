from __future__ import annotations

from pathlib import Path

from PIL import ImageDraw, ImageFont


def load_font(
    size: int,
    *,
    bold: bool = False,
    italic: bool = False,
    monospace: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _font_candidates(bold=bold, italic=italic, monospace=monospace):
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def font_line_height(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    return max(1, font_ascent(font) + font_descent(font) + 6)


def font_ascent(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    if hasattr(font, "getmetrics"):
        ascent, _ = font.getmetrics()
        return max(1, ascent)
    bbox = font.getbbox("H")
    return max(1, bbox[3] - bbox[1])


def font_descent(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    if hasattr(font, "getmetrics"):
        _, descent = font.getmetrics()
        return max(0, descent)
    bbox = font.getbbox("g")
    return max(0, bbox[3])


def text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    if not text:
        return 0
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


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
