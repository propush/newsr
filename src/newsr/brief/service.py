from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from ..cancellation import RefreshCancellation
from ..config.models import AppConfig
from ..domain import ArticleRecord, ProviderRecord, ReaderState, ViewMode
from ..storage.facade import NewsStorage


class BriefPeriod(StrEnum):
    LAST_24H = "last_24h"
    LAST_WEEK = "last_week"
    ALL_UNREAD = "all_unread"


@dataclass(frozen=True, slots=True)
class BriefOptions:
    period: BriefPeriod = BriefPeriod.LAST_24H
    include_topics: bool = False
    mark_read: bool = True


@dataclass(frozen=True, slots=True)
class BriefArticle:
    article_id: str
    provider_id: str
    provider_name: str
    title: str
    summary: str
    published_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class BriefProgress:
    completed: int
    total: int
    status: str


@dataclass(frozen=True, slots=True)
class BriefResult:
    report: str
    articles: list[BriefArticle]
    provider_ids: list[str]


ProgressCallback = Callable[[BriefProgress], None]

_MIN_OUTPUT_TOKENS = 16
_MAX_BATCH_OUTPUT_TOKENS = 1024
_MAX_FINAL_OUTPUT_TOKENS = 2048


class BriefService:
    def __init__(self, config: AppConfig, storage: NewsStorage, llm_client) -> None:  # type: ignore[no-untyped-def]
        self._config = config
        self._storage = storage
        self._llm_client = llm_client

    def generate(
        self,
        options: BriefOptions,
        *,
        now: datetime | None = None,
        cancellation: RefreshCancellation | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BriefResult:
        self._raise_if_cancelled(cancellation)
        articles = self.select_articles(options, now=now)
        provider_ids = self._selected_provider_ids(options)
        if not articles:
            report = self._empty_report(options)
            if options.mark_read:
                self.mark_sources_read(provider_ids)
            return BriefResult(report=report, articles=[], provider_ids=provider_ids)

        notes = self._summarize_articles(articles, cancellation, on_progress)
        report = self._synthesize_report(notes, cancellation, on_progress)
        report = self._append_statistics(report, articles, provider_ids)
        self._raise_if_cancelled(cancellation)
        if options.mark_read:
            self.mark_sources_read(provider_ids)
        return BriefResult(report=report, articles=articles, provider_ids=provider_ids)

    def select_articles(self, options: BriefOptions, *, now: datetime | None = None) -> list[BriefArticle]:
        selected_providers = self._selected_providers(options)
        provider_by_id = {provider.provider_id: provider for provider in selected_providers}
        if not provider_by_id:
            return []

        translated_records = [
            article
            for article in self._storage.list_articles()
            if article.provider_id in provider_by_id and self._is_translated(article)
        ]
        records = [article for article in translated_records if self._has_completed_summary(article)]
        if options.period == BriefPeriod.ALL_UNREAD:
            unread_ids = {
                article.article_id
                for article in self._unread_records(translated_records, set(provider_by_id))
            }
            records = [article for article in records if article.article_id in unread_ids]
        else:
            cutoff = self._cutoff_for_period(options.period, now or datetime.now(UTC))
            records = [article for article in records if self._article_timestamp(article) >= cutoff]

        return [self._brief_article(article, provider_by_id[article.provider_id]) for article in records]

    def mark_articles_read(self, articles: Sequence[BriefArticle]) -> None:
        latest_by_provider: dict[str, BriefArticle] = {}
        for article in articles:
            latest_by_provider[article.provider_id] = article
        for provider_id, article in latest_by_provider.items():
            self._storage.save_reader_state(
                provider_id,
                ReaderState(article_id=article.article_id, view_mode=ViewMode.FULL, scroll_offset=0),
            )

    def mark_sources_read(self, provider_ids: Sequence[str]) -> None:
        provider_id_set = set(provider_ids)
        if not provider_id_set:
            return
        latest_by_provider: dict[str, ArticleRecord] = {}
        for article in self._storage.list_articles():
            if article.provider_id in provider_id_set and self._is_translated(article):
                latest_by_provider[article.provider_id] = article
        for provider_id, article in latest_by_provider.items():
            self._storage.save_reader_state(
                provider_id,
                ReaderState(article_id=article.article_id, view_mode=ViewMode.FULL, scroll_offset=0),
            )

    def _summarize_articles(
        self,
        articles: Sequence[BriefArticle],
        cancellation: RefreshCancellation | None,
        on_progress: ProgressCallback | None,
    ) -> list[str]:
        output_tokens = self._batch_output_tokens()
        prompt = self._batch_prompt()
        input_budget = self._input_budget(prompt, output_tokens)
        entries = [self._format_article(article, input_budget) for article in articles]
        batches = self._batch_texts(entries, input_budget)
        total = len(batches) + 1
        notes: list[str] = []
        for index, batch in enumerate(batches, start=1):
            self._raise_if_cancelled(cancellation)
            self._emit(on_progress, index - 1, total, f"compressing summaries {index} of {len(batches)}")
            notes.append(
                self._llm_client.shorten_brief_notes(
                    prompt,
                    batch,
                    max_tokens=output_tokens,
                    cancellation=cancellation,
                )
            )
        return self._reduce_notes(notes, cancellation, on_progress)

    def _reduce_notes(
        self,
        notes: list[str],
        cancellation: RefreshCancellation | None,
        on_progress: ProgressCallback | None,
    ) -> list[str]:
        output_tokens = self._batch_output_tokens()
        batch_prompt = self._batch_prompt()
        final_prompt = self._final_prompt()
        input_budget = self._input_budget(batch_prompt, output_tokens)
        for iteration in range(1, 21):
            self._raise_if_cancelled(cancellation)
            if self._fits(final_prompt, "\n\n".join(notes), self._final_output_tokens()):
                return notes
            batches = self._batch_texts(notes, input_budget)
            reduced: list[str] = []
            for index, batch in enumerate(batches, start=1):
                self._emit(on_progress, index, len(batches) + 1, f"reducing notes pass {iteration}")
                reduced.append(
                    self._llm_client.shorten_brief_notes(
                        batch_prompt,
                        self._trim_to_budget(batch, input_budget),
                        max_tokens=output_tokens,
                        cancellation=cancellation,
                    )
                )
            if len(reduced) == len(notes) and sum(map(len, reduced)) >= sum(map(len, notes)):
                return [self._trim_to_budget("\n\n".join(reduced), input_budget)]
            notes = reduced
        return [self._trim_to_budget("\n\n".join(notes), input_budget)]

    def _synthesize_report(
        self,
        notes: Sequence[str],
        cancellation: RefreshCancellation | None,
        on_progress: ProgressCallback | None,
    ) -> str:
        output_tokens = self._final_output_tokens()
        prompt = self._final_prompt()
        input_budget = self._input_budget(prompt, output_tokens)
        content = self._trim_to_budget("\n\n".join(notes), input_budget)
        self._raise_if_cancelled(cancellation)
        self._emit(on_progress, 1, 1, "writing final brief")
        return self._llm_client.synthesize_brief_report(
            prompt,
            content,
            max_tokens=output_tokens,
            cancellation=cancellation,
        )

    def _batch_prompt(self) -> str:
        return (
            "Shorten these news summaries into compact brief notes in "
            f"{self._config.translation.target_language}. "
            "Keep only distinct important facts. Return concise Markdown bullets."
        )

    def _final_prompt(self) -> str:
        return (
            f"Markdown brief in {self._config.translation.target_language}: "
            "# title; ## topic sections separated by ---; bullets per topic. "
            "Group related items, remove repetition."
        )

    def _selected_provider_ids(self, options: BriefOptions) -> list[str]:
        return [provider.provider_id for provider in self._selected_providers(options)]

    def _selected_providers(self, options: BriefOptions) -> list[ProviderRecord]:
        allowed_types = {"http", "topic"} if options.include_topics else {"http"}
        return [
            provider
            for provider in self._storage.list_enabled_providers()
            if provider.provider_type in allowed_types
        ]

    def _unread_records(self, records: list[ArticleRecord], provider_ids: set[str]) -> list[ArticleRecord]:
        unread: list[ArticleRecord] = []
        for provider_id in provider_ids:
            provider_records = [article for article in records if article.provider_id == provider_id]
            state = self._storage.load_reader_state(provider_id)
            unread.extend(self._after_reader_state(provider_records, state.article_id))
        return [article for article in records if article in unread]

    @staticmethod
    def _after_reader_state(records: list[ArticleRecord], article_id: str | None) -> list[ArticleRecord]:
        if article_id is None:
            return records
        for index, article in enumerate(records):
            if article.article_id == article_id:
                return records[index + 1 :]
        return records

    @staticmethod
    def _is_translated(article: ArticleRecord) -> bool:
        return (
            article.translation_status == "done"
            and article.translated_body is not None
        )

    @staticmethod
    def _has_completed_summary(article: ArticleRecord) -> bool:
        return (
            article.summary_status == "done"
            and bool((article.summary or "").strip())
        )

    @staticmethod
    def _cutoff_for_period(period: BriefPeriod, now: datetime) -> datetime:
        normalized_now = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
        if period == BriefPeriod.LAST_24H:
            return normalized_now - timedelta(hours=24)
        return normalized_now - timedelta(days=7)

    @staticmethod
    def _article_timestamp(article: ArticleRecord) -> datetime:
        value = article.published_at or article.created_at
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)

    @staticmethod
    def _brief_article(article: ArticleRecord, provider: ProviderRecord) -> BriefArticle:
        return BriefArticle(
            article_id=article.article_id,
            provider_id=article.provider_id,
            provider_name=provider.display_name,
            title=article.translated_title or article.title,
            summary=(article.summary or "").strip(),
            published_at=article.published_at,
            created_at=article.created_at,
        )

    def _format_article(self, article: BriefArticle, input_budget: int) -> str:
        timestamp = article.published_at or article.created_at
        prefix = (
            f"Provider: {article.provider_name}\n"
            f"Title: {article.title}\n"
            f"Published: {timestamp.astimezone().strftime('%Y-%m-%d %H:%M %Z')}\n"
            "Summary:\n"
        )
        remaining = max(1, input_budget - estimate_token_count(prefix) - 1)
        return prefix + self._trim_to_budget(article.summary, remaining)

    def _batch_texts(self, values: Sequence[str], input_budget: int) -> list[str]:
        batches: list[str] = []
        current: list[str] = []
        current_tokens = 0
        for value in values:
            text = self._trim_to_budget(value, input_budget)
            token_count = estimate_token_count(text)
            separator_tokens = 1 if current else 0
            if current and current_tokens + separator_tokens + token_count > input_budget:
                batches.append("\n\n".join(current))
                current = []
                current_tokens = 0
            current.append(text)
            current_tokens += token_count + separator_tokens
        if current:
            batches.append("\n\n".join(current))
        return batches

    def _batch_output_tokens(self) -> int:
        return max(_MIN_OUTPUT_TOKENS, min(_MAX_BATCH_OUTPUT_TOKENS, self._config.llm.brief_context // 4))

    def _final_output_tokens(self) -> int:
        return max(_MIN_OUTPUT_TOKENS, min(_MAX_FINAL_OUTPUT_TOKENS, self._config.llm.brief_context // 3))

    def _input_budget(self, prompt: str, output_tokens: int) -> int:
        prompt_tokens = estimate_token_count(prompt)
        budget = self._config.llm.brief_context - prompt_tokens - output_tokens
        if budget <= 0:
            raise ValueError("llm.brief_context is too small for brief generation")
        return budget

    def _fits(self, prompt: str, content: str, output_tokens: int) -> bool:
        return estimate_token_count(prompt) + estimate_token_count(content) + output_tokens <= self._config.llm.brief_context

    @staticmethod
    def _trim_to_budget(value: str, token_budget: int) -> str:
        if estimate_token_count(value) <= token_budget:
            return value
        char_budget = max(1, token_budget * 3)
        return value[:char_budget].rsplit(" ", 1)[0].strip() or value[:char_budget].strip()

    @staticmethod
    def _empty_report(options: BriefOptions) -> str:
        period = {
            BriefPeriod.LAST_24H: "last 24 hours",
            BriefPeriod.LAST_WEEK: "last week",
            BriefPeriod.ALL_UNREAD: "all unread articles",
        }[options.period]
        return f"# Brief\n\nNo completed article summaries were found for {period}."

    @staticmethod
    def _append_statistics(
        report: str,
        articles: Sequence[BriefArticle],
        provider_ids: Sequence[str],
    ) -> str:
        counts_by_provider: dict[str, int] = {}
        names_by_provider: dict[str, str] = {}
        for article in articles:
            counts_by_provider[article.provider_id] = (
                counts_by_provider.get(article.provider_id, 0) + 1
            )
            names_by_provider.setdefault(article.provider_id, article.provider_name)

        lines = [
            f"{names_by_provider[provider_id]}: {counts_by_provider[provider_id]}"
            for provider_id in provider_ids
            if provider_id in counts_by_provider
        ]
        if not lines:
            return report
        return f"{report.rstrip()}\n\n## Statistics\n\n" + "\n\n".join(lines)

    @staticmethod
    def _emit(callback: ProgressCallback | None, completed: int, total: int, status: str) -> None:
        if callback is not None:
            callback(BriefProgress(completed=completed, total=max(1, total), status=status))

    @staticmethod
    def _raise_if_cancelled(cancellation: RefreshCancellation | None) -> None:
        if cancellation is not None:
            cancellation.raise_if_cancelled()


def estimate_token_count(value: str) -> int:
    return max(1, (len(value.encode("utf-8")) + 2) // 3)
