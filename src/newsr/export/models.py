from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ExportAction(StrEnum):
    SAVE_PNG = "save_png"
    COPY_PNG = "copy_png"
    SAVE_MARKDOWN = "save_markdown"
    COPY_MARKDOWN = "copy_markdown"


@dataclass(slots=True)
class ExportTheme:
    background: str
    panel: str
    foreground: str
    primary: str
    secondary: str
    accent: str


@dataclass(slots=True)
class ExportDocument:
    article_id: str
    title: str
    date_text: str
    provider_name: str
    category: str
    mode_label: str
    source_url: str
    body: str
    filename_stem: str
    theme: ExportTheme


@dataclass(slots=True)
class ExportResult:
    success: bool
    message: str
    output_path: Path | None = None
