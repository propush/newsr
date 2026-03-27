from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from textual.color import Color
from textual.theme import Theme

from ..config import AppConfig
from ..domain import ArticleRecord, ViewMode
from ..providers.registry import build_provider_registry
from .clipboard import ClipboardError, ClipboardManager
from .models import ExportAction, ExportDocument, ExportResult, ExportTheme
from .png_renderer import PillowPngRenderer


class PngRenderer(Protocol):
    def render(self, document: ExportDocument, quality: str) -> bytes: ...


class ExportService:
    _FALLBACK_PROVIDER_NAME = "Unknown"

    def __init__(
        self,
        *,
        exports_root: Path | None = None,
        clipboard: ClipboardManager | None = None,
        png_renderer: PngRenderer | None = None,
    ) -> None:
        self.exports_root = exports_root or Path.cwd() / "exports"
        self.clipboard = clipboard or ClipboardManager()
        self.png_renderer = png_renderer or PillowPngRenderer()

    def export(
        self,
        action: ExportAction,
        *,
        article: ArticleRecord,
        view_mode: ViewMode,
        theme: Theme,
        config: AppConfig,
    ) -> ExportResult:
        document = self._build_document(article=article, view_mode=view_mode, theme=theme)
        if action == ExportAction.SAVE_MARKDOWN:
            return self._save_markdown(document)
        if action == ExportAction.COPY_MARKDOWN:
            return self._copy_markdown(document)
        if action == ExportAction.SAVE_PNG:
            return self._save_png(document, config.export.image.quality)
        if action == ExportAction.COPY_PNG:
            return self._copy_png(document, config.export.image.quality)
        raise ValueError(f"unsupported export action: {action}")

    def _save_markdown(self, document: ExportDocument) -> ExportResult:
        target = self._target_path(document, extension="md")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self._render_markdown(document), encoding="utf-8")
        return ExportResult(True, f"saved markdown export to {target}", output_path=target)

    def _copy_markdown(self, document: ExportDocument) -> ExportResult:
        try:
            self.clipboard.copy_text(self._render_markdown(document))
        except ClipboardError as exc:
            return ExportResult(False, str(exc))
        return ExportResult(True, "copied markdown export to clipboard")

    def _save_png(self, document: ExportDocument, quality: str) -> ExportResult:
        target = self._target_path(document, extension="png")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.png_renderer.render(document, quality))
        return ExportResult(True, f"saved png export to {target}", output_path=target)

    def _copy_png(self, document: ExportDocument, quality: str) -> ExportResult:
        try:
            self.clipboard.copy_image(self.png_renderer.render(document, quality))
        except ClipboardError as exc:
            return ExportResult(False, str(exc))
        return ExportResult(True, "copied png export to clipboard")

    def _target_path(self, document: ExportDocument, *, extension: str) -> Path:
        return self.exports_root / f"{document.filename_stem}.{extension}"

    def _render_markdown(self, document: ExportDocument) -> str:
        return (
            f"# {document.title}\n\n"
            f"Date: {document.date_text}\n"
            f"Provider: {document.provider_name}\n"
            f"Category: {document.category}\n"
            f"Mode: {document.mode_label}\n"
            f"URL: {document.source_url}\n\n"
            f"{document.body}"
        )

    def _build_document(self, *, article: ArticleRecord, view_mode: ViewMode, theme: Theme) -> ExportDocument:
        mode_label = "summary" if view_mode == ViewMode.SUMMARY and article.summary else "full"
        body = article.summary if mode_label == "summary" and article.summary else article.translated_body or article.source_body
        title = article.translated_title or article.title
        date = article.published_at or article.created_at
        date_text = date.astimezone().strftime("%Y-%m-%d %H:%M %Z")
        slug = self._slugify(article.article_id)
        return ExportDocument(
            article_id=article.article_id,
            title=title,
            date_text=date_text,
            provider_name=self._provider_name(article),
            category=article.category,
            mode_label=mode_label,
            source_url=article.url,
            body=body,
            filename_stem=f"{date.astimezone().strftime('%Y-%m-%d')}_{slug}_{mode_label}",
            theme=self._resolve_theme(theme),
        )

    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "article"

    @classmethod
    def _provider_name(cls, article: ArticleRecord) -> str:
        provider_id = article.provider_id.strip()
        if not provider_id:
            return cls._FALLBACK_PROVIDER_NAME
        provider = build_provider_registry().get(provider_id)
        if provider is not None:
            return provider.display_name
        return provider_id

    def _resolve_theme(self, theme: Theme) -> ExportTheme:
        background = theme.background or ("#0f1115" if theme.dark else "#ffffff")
        foreground = theme.foreground or ("#f4f4f4" if theme.dark else "#101010")
        panel = theme.panel or theme.surface or self._mix(background, foreground, 0.08 if theme.dark else 0.04)
        secondary = theme.secondary or self._mix(foreground, background, 0.35)
        accent = theme.accent or theme.primary
        return ExportTheme(
            background=background,
            panel=panel,
            foreground=foreground,
            primary=theme.primary,
            secondary=secondary,
            accent=accent,
        )

    @staticmethod
    def _mix(top: str, bottom: str, ratio: float) -> str:
        top_color = Color.parse(top)
        bottom_color = Color.parse(bottom)
        red = int((top_color.r * (1 - ratio)) + (bottom_color.r * ratio))
        green = int((top_color.g * (1 - ratio)) + (bottom_color.g * ratio))
        blue = int((top_color.b * (1 - ratio)) + (bottom_color.b * ratio))
        return f"#{red:02X}{green:02X}{blue:02X}"
