from __future__ import annotations

from rich.cells import cell_len
from rich.style import Style
from rich.text import Text

from typing import TYPE_CHECKING

from ...domain import ArticleRecord
from ...domain.reader import ReaderState, ViewMode
from ...ui_text import UILocalizer

if TYPE_CHECKING:
    from ...providers.base import NewsProvider
    from ...storage.facade import NewsStorage


def article_text(reader_state: ReaderState, article: ArticleRecord) -> str:
    if reader_state.view_mode == ViewMode.SUMMARY and article.summary:
        return article.summary
    return article.translated_body or article.source_body


def view_mode_label(ui: UILocalizer, reader_state: ReaderState, article: ArticleRecord) -> str:
    if reader_state.view_mode == ViewMode.SUMMARY and article.summary:
        return ui.text("app.article.mode.summary")
    return ui.text("app.article.mode.full")


def article_header(
    ui: UILocalizer,
    current_index: int,
    total: int,
    article: ArticleRecord,
    reader_state: ReaderState,
    accent_color: str,
) -> Text:
    date_text = format_article_date(article)
    title = article.translated_title or article.title
    mode = view_mode_label(ui, reader_state, article)
    article_position = current_index + 1
    header = Text(ui.text("app.article.position", current=article_position, total=total))
    if article.categories:
        header.append("  ")
        category_style = Style(color=accent_color, bold=True)
        for index, category in enumerate(article.categories):
            if index:
                header.append(" ")
            header.append(f"[{category}]", style=category_style)
    lines = [
        header,
        Text(ui.text("app.article.date", date=date_text)),
        Text(ui.text("app.article.title", title=title)),
        Text(ui.text("app.article.mode", mode=mode)),
    ]
    return Text("\n").join(lines)


def article_frame_title(
    article: ArticleRecord,
    width: int,
    providers: dict[str, NewsProvider],
) -> str | None:
    category = article.category.strip()
    source_label = article_source_label(article, providers)
    if not category and source_label is None:
        return None
    if source_label is None:
        return category if category else None
    left = f"{source_label} "
    if not category:
        return source_label
    right = f" {category}"
    available = max(1, width - 4)
    minimum_gap = 1
    max_left = max(1, available - cell_len(right) - minimum_gap)
    if cell_len(left) > max_left:
        left = truncate_cells(left, max_left)
    gap = max(minimum_gap, available - cell_len(left) - cell_len(right))
    return f"{left}{'━' * gap}{right}"


def article_source_label(article: ArticleRecord, providers: dict[str, NewsProvider]) -> str | None:
    author = article.author.strip() if article.author and article.author.strip() else None
    provider_label = None
    if article.provider_id and article.provider_id.strip():
        provider_id = article.provider_id.strip()
        provider = providers.get(provider_id)
        provider_label = provider.display_name if provider is not None else provider_id
    if author and provider_label:
        return f"{author} @ {provider_label}"
    if provider_label:
        return provider_label
    return author


def article_url_text(ui: UILocalizer, article: ArticleRecord, width: int | None = None) -> str:
    value = ui.text("app.article.url", url=article.url)
    if width is None or width <= 0:
        return value
    return truncate_middle_cells(value, width)


def format_article_date(article: ArticleRecord) -> str:
    date = article.published_at or article.created_at
    return date.astimezone().strftime("%Y-%m-%d %H:%M %Z")


def provider_display_names(storage: NewsStorage) -> dict[str, str]:
    return {
        provider.provider_id: provider.display_name
        for provider in storage.list_providers()
    }


def visible_status_text(status_text: str, viewport_width: int, status_busy: bool) -> str:
    if viewport_width <= 0:
        return status_text
    status_bar_padding = 2
    busy_indicator_width = 4 if status_busy else 0
    available = max(1, viewport_width - status_bar_padding - busy_indicator_width)
    return format_status_text(status_text, available)


def format_status_text(value: str, max_cells: int) -> str:
    if max_cells <= 0 or cell_len(value) <= max_cells:
        return value
    progress_marker = ", done "
    progress_index = value.rfind(progress_marker)
    if progress_index == -1:
        return truncate_middle_cells(value, max_cells)

    progress = value[progress_index + 2:]
    separator = "… "
    if cell_len(progress) + cell_len(separator) >= max_cells:
        return truncate_cells(progress, max_cells)

    prefix_width = max_cells - cell_len(progress) - cell_len(separator)
    prefix = fit_cells(value[:progress_index], prefix_width)
    return f"{prefix}{separator}{progress}"


def truncate_cells(text: str, max_cells: int) -> str:
    if max_cells <= 0:
        return ""
    if cell_len(text) <= max_cells:
        return text
    if max_cells == 1:
        return "…"
    return f"{fit_cells(text, max_cells - 1)}…"


def truncate_middle_cells(text: str, max_cells: int) -> str:
    if max_cells <= 0:
        return ""
    if cell_len(text) <= max_cells:
        return text
    if max_cells == 1:
        return "…"
    prefix_width = max(1, (max_cells - 1) // 2)
    suffix_width = max(1, max_cells - prefix_width - 1)
    prefix = fit_cells(text, prefix_width)
    suffix = fit_cells(text, suffix_width, from_end=True)
    return f"{prefix}…{suffix}"


def fit_cells(text: str, max_cells: int, *, from_end: bool = False) -> str:
    if max_cells <= 0:
        return ""
    if cell_len(text) <= max_cells:
        return text
    fitted = ""
    characters = reversed(text) if from_end else text
    for character in characters:
        if cell_len(character + fitted if from_end else fitted + character) > max_cells:
            break
        fitted = character + fitted if from_end else fitted + character
    return fitted
