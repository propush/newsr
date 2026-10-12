from __future__ import annotations

from ...domain.articles import ArticleRecord

PROVIDER_COLUMN_WIDTH = 16
CATEGORY_COLUMN_WIDTH = 16
DATE_COLUMN_WIDTH = 10


def title_column_width(screen_width: int) -> int:
    return max(12, screen_width - PROVIDER_COLUMN_WIDTH - CATEGORY_COLUMN_WIDTH - 20)


def format_short_article_date(article: ArticleRecord) -> str:
    date = article.published_at or article.created_at
    return date.astimezone().strftime("%Y-%m-%d")


def trimmed_title(article: ArticleRecord, width: int) -> str:
    title = article.translated_title or article.title or ""
    if len(title) <= width:
        return title
    if width <= 3:
        return title[:width]
    return f"{title[: width - 3]}..."


def provider_label(article: ArticleRecord, provider_display_names: dict[str, str]) -> str:
    provider_id = article.provider_id.strip()
    if not provider_id:
        return ""
    return provider_display_names.get(provider_id, provider_id)
