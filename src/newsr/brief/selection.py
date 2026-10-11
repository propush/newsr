from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from ..domain import ArticleRecord, ProviderRecord
from ..storage.facade import NewsStorage
from .models import BriefArticle, BriefOptions, BriefPeriod


class BriefArticleSelector:
    def __init__(self, storage: NewsStorage) -> None:
        self._storage = storage

    def select_articles(self, options: BriefOptions, *, now: datetime | None = None) -> list[BriefArticle]:
        selected_providers = self.selected_providers(options)
        provider_by_id = {provider.provider_id: provider for provider in selected_providers}
        if not provider_by_id:
            return []

        translated_records = [
            article
            for article in self._storage.list_articles()
            if article.provider_id in provider_by_id and _is_translated(article)
        ]
        records = [article for article in translated_records if _has_completed_summary(article)]
        if options.period == BriefPeriod.ALL_UNREAD or options.only_unread:
            unread_ids = {
                article.article_id
                for article in self._unread_records(translated_records, set(provider_by_id))
            }
            records = [article for article in records if article.article_id in unread_ids]
        if options.period != BriefPeriod.ALL_UNREAD:
            cutoff = _cutoff_for_period(options.period, now or datetime.now(UTC))
            records = [article for article in records if _article_timestamp(article) >= cutoff]

        return [
            _brief_article(index, article, provider_by_id[article.provider_id])
            for index, article in enumerate(records, start=1)
        ]

    def selected_provider_ids(self, options: BriefOptions) -> list[str]:
        return [provider.provider_id for provider in self.selected_providers(options)]

    def selected_providers(self, options: BriefOptions) -> list[ProviderRecord]:
        allowed_types = {"http", "topic"} if options.include_topics else {"http"}
        return [
            provider
            for provider in self._storage.list_enabled_providers()
            if provider.provider_type in allowed_types
        ]

    def mark_articles_read(self, articles: Sequence[BriefArticle]) -> None:
        latest_by_provider: dict[str, BriefArticle] = {}
        for article in articles:
            latest_by_provider[article.provider_id] = article
        for provider_id, article in latest_by_provider.items():
            self._mark_provider_read(provider_id, article.article_id)

    def mark_sources_read(self, provider_ids: Sequence[str]) -> None:
        provider_id_set = set(provider_ids)
        if not provider_id_set:
            return
        latest_by_provider: dict[str, ArticleRecord] = {}
        for article in self._storage.list_articles():
            if article.provider_id in provider_id_set and _is_translated(article):
                latest_by_provider[article.provider_id] = article
        for provider_id, article in latest_by_provider.items():
            self._mark_provider_read(provider_id, article.article_id)

    def _mark_provider_read(self, provider_id: str, article_id: str) -> None:
        state = self._storage.load_reader_state(provider_id)
        state.article_id = article_id
        state.scroll_offset = 0
        self._storage.save_reader_state(provider_id, state)

    def _unread_records(self, records: list[ArticleRecord], provider_ids: set[str]) -> list[ArticleRecord]:
        unread: list[ArticleRecord] = []
        for provider_id in provider_ids:
            provider_records = [article for article in records if article.provider_id == provider_id]
            state = self._storage.load_reader_state(provider_id)
            unread.extend(_after_reader_state(provider_records, state.article_id))
        return [article for article in records if article in unread]


def _after_reader_state(records: list[ArticleRecord], article_id: str | None) -> list[ArticleRecord]:
    if article_id is None:
        return records
    for index, article in enumerate(records):
        if article.article_id == article_id:
            return records[index + 1 :]
    return records


def _is_translated(article: ArticleRecord) -> bool:
    return (
        article.translation_status == "done"
        and article.translated_body is not None
    )


def _has_completed_summary(article: ArticleRecord) -> bool:
    return (
        article.summary_status == "done"
        and bool((article.summary or "").strip())
    )


def _cutoff_for_period(period: BriefPeriod, now: datetime) -> datetime:
    normalized_now = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
    if period == BriefPeriod.LAST_24H:
        return normalized_now - timedelta(hours=24)
    return normalized_now - timedelta(days=7)


def _article_timestamp(article: ArticleRecord) -> datetime:
    value = article.published_at or article.created_at
    return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)


def _brief_article(number: int, article: ArticleRecord, provider: ProviderRecord) -> BriefArticle:
    return BriefArticle(
        number=number,
        article_id=article.article_id,
        provider_id=article.provider_id,
        provider_name=provider.display_name,
        title=article.translated_title or article.title,
        summary=(article.summary or "").strip(),
        published_at=article.published_at,
        created_at=article.created_at,
    )
