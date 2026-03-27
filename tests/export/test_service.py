from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from PIL import Image

from newsr.config import AppConfig
from newsr.domain import ArticleRecord, ViewMode
from newsr.export import ExportAction, ExportService
from newsr.ui import OLD_FIDO_THEME


class FakeClipboard:
    def __init__(self) -> None:
        self.text: str | None = None
        self.image: bytes | None = None

    def copy_text(self, text: str) -> None:
        self.text = text

    def copy_image(self, png_bytes: bytes) -> None:
        self.image = png_bytes


def make_article(*, body: str = "Body text", summary: str | None = "Summary text") -> ArticleRecord:
    return ArticleRecord(
        article_id="world-1",
        url="https://www.bbc.com/news/world-1",
        category="world",
        title="Source title",
        translated_title="Translated title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        source_body="Source body",
        translated_body=body,
        summary=summary,
        more_info=None,
        translation_status="done",
        summary_status="done" if summary else "pending",
        created_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        provider_id="bbc",
    )


def test_export_service_saves_markdown_with_metadata_and_unmodified_body(tmp_path: Path, app_config: AppConfig) -> None:
    article = make_article(body="**Body** line 1\n\nLine 2")
    service = ExportService(exports_root=tmp_path / "exports", clipboard=FakeClipboard())
    expected_date = article.published_at.astimezone().strftime("%Y-%m-%d %H:%M %Z")

    result = service.export(
        ExportAction.SAVE_MARKDOWN,
        article=article,
        view_mode=ViewMode.FULL,
        theme=OLD_FIDO_THEME,
        config=app_config,
    )

    assert result.success is True
    assert result.output_path is not None
    content = result.output_path.read_text(encoding="utf-8")
    assert content.startswith(f"# Translated title\n\nDate: {expected_date}")
    assert "Provider: BBC News" in content
    assert "Category: world" in content
    assert "Mode: full" in content
    assert content.endswith("**Body** line 1\n\nLine 2")


def test_export_service_uses_summary_body_for_summary_mode(tmp_path: Path, app_config: AppConfig) -> None:
    article = make_article(body="Full article", summary="Short summary")
    service = ExportService(exports_root=tmp_path / "exports", clipboard=FakeClipboard())

    result = service.export(
        ExportAction.SAVE_MARKDOWN,
        article=article,
        view_mode=ViewMode.SUMMARY,
        theme=OLD_FIDO_THEME,
        config=app_config,
    )

    assert result.success is True
    assert result.output_path is not None
    assert result.output_path.name.endswith("_summary.md")
    assert result.output_path.read_text(encoding="utf-8").endswith("Short summary")


def test_export_service_saves_hd_png_with_phone_width(tmp_path: Path, app_config: AppConfig) -> None:
    article = make_article(body="\n\n".join(f"Paragraph {index}" for index in range(120)))
    service = ExportService(exports_root=tmp_path / "exports", clipboard=FakeClipboard())

    result = service.export(
        ExportAction.SAVE_PNG,
        article=article,
        view_mode=ViewMode.FULL,
        theme=OLD_FIDO_THEME,
        config=app_config,
    )

    assert result.success is True
    assert result.output_path is not None
    with Image.open(result.output_path) as image:
        assert image.width == 720
        assert image.height >= 1280


def test_export_service_copies_png_to_clipboard(tmp_path: Path, app_config: AppConfig) -> None:
    clipboard = FakeClipboard()
    service = ExportService(exports_root=tmp_path / "exports", clipboard=clipboard)

    result = service.export(
        ExportAction.COPY_PNG,
        article=make_article(),
        view_mode=ViewMode.FULL,
        theme=OLD_FIDO_THEME,
        config=app_config,
    )

    assert result.success is True
    assert clipboard.image is not None
    with Image.open(BytesIO(clipboard.image)) as image:
        assert image.width == 720


def test_export_service_copies_markdown_to_clipboard(tmp_path: Path, app_config: AppConfig) -> None:
    clipboard = FakeClipboard()
    service = ExportService(exports_root=tmp_path / "exports", clipboard=clipboard)

    result = service.export(
        ExportAction.COPY_MARKDOWN,
        article=make_article(body="Copied body"),
        view_mode=ViewMode.FULL,
        theme=OLD_FIDO_THEME,
        config=app_config,
    )

    assert result.success is True
    assert clipboard.text is not None
    assert "Provider: BBC News" in clipboard.text
    assert clipboard.text.endswith("Copied body")


def test_export_service_renders_markdown_body_to_png(tmp_path: Path, app_config: AppConfig) -> None:
    article = make_article(
        body=(
            "# Heading\n\n"
            "Paragraph with **bold** text, *italic* text, `code`, and [a link](https://example.com).\n\n"
            "- first item\n"
            "- second item\n\n"
            "```python\n"
            "print('hello world')\n"
            "```\n\n"
            "> quoted line"
        )
    )
    service = ExportService(exports_root=tmp_path / "exports", clipboard=FakeClipboard())

    result = service.export(
        ExportAction.SAVE_PNG,
        article=article,
        view_mode=ViewMode.FULL,
        theme=OLD_FIDO_THEME,
        config=app_config,
    )

    assert result.success is True
    assert result.output_path is not None
    with Image.open(result.output_path) as image:
        assert image.width == 720
        assert image.height >= 1280
