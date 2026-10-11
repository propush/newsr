from __future__ import annotations

from datetime import UTC, datetime

from newsr.domain import ArticleContent
from newsr.ui import NewsReaderApp


def seed_provider_article(
    app: NewsReaderApp,
    *,
    provider_id: str,
    provider_article_id: str,
    title: str,
    body: str,
    minute: int,
    translated_title: str | None = None,
) -> str:
    article_id = f"{provider_id}:{provider_article_id}"
    article = ArticleContent(
        article_id=article_id,
        provider_id=provider_id,
        provider_article_id=provider_article_id,
        url=f"https://example.com/{provider_id}/{provider_article_id}",
        category="world",
        title=title,
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, minute, tzinfo=UTC),
        body=body,
    )
    app.storage.upsert_article_source(article)
    app.storage.update_translation(article_id, translated_title or title, body, "done")
    app.storage.update_summary(article_id, f"Summary for {title}", "done")
    return article_id


def disable_startup_refresh(app: NewsReaderApp) -> None:
    app._refresh.start = lambda *args, **kwargs: None  # type: ignore[method-assign]
