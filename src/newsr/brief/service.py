from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from time import perf_counter

from ..cancellation import RefreshCancellation
from ..config.models import AppConfig
from ..domain import ArticleRecord, ProviderRecord, ReaderState, ViewMode
from ..providers.llm.client import current_datetime_prompt_value
from ..storage.facade import NewsStorage
from .repair import (
    MAX_BRIEF_REPAIR_ATTEMPTS,
    SOURCE_REF_RE,
    BriefValidation,
    format_numbers,
    format_validation,
    reference_numbers,
    remove_invalid_references,
    remove_unreferenced_statement_lines,
    validate_brief_text,
)


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
    number: int
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
    message_key: str
    message_args: dict[str, object]


@dataclass(frozen=True, slots=True)
class BriefResult:
    report: str
    articles: list[BriefArticle]
    provider_ids: list[str]


@dataclass(frozen=True, slots=True)
class _BriefBatch:
    text: str
    article_numbers: frozenset[int]
    articles: tuple[BriefArticle, ...] = ()


ProgressCallback = Callable[[BriefProgress], None]
Clock = Callable[[], datetime]

_MIN_OUTPUT_TOKENS = 16
_MAX_BATCH_OUTPUT_TOKENS = 1024
_MAX_FINAL_OUTPUT_TOKENS = 2048
LOGGER = logging.getLogger("newsr.llm")


class BriefService:
    def __init__(
        self,
        config: AppConfig,
        storage: NewsStorage,
        llm_client,
        *,
        current_time: Clock | None = None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._config = config
        self._storage = storage
        self._llm_client = llm_client
        self._current_time = current_time

    def generate(
        self,
        options: BriefOptions,
        *,
        now: datetime | None = None,
        cancellation: RefreshCancellation | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BriefResult:
        started_at = perf_counter()
        self._raise_if_cancelled(cancellation)
        self._emit(on_progress, 0, 1, "brief.status.selecting_articles")
        articles = self.select_articles(options, now=now)
        provider_ids = self._selected_provider_ids(options)
        LOGGER.info(
            "brief_generate_start period=%s include_topics=%s mark_read=%s articles=%s providers=%s",
            options.period,
            options.include_topics,
            options.mark_read,
            len(articles),
            len(provider_ids),
        )
        if not articles:
            report = self._empty_report(options)
            if options.mark_read:
                self._emit(on_progress, 0, 1, "brief.status.marking_read")
                self.mark_sources_read(provider_ids)
            LOGGER.info(
                "brief_generate_done articles=0 providers=%s duration_s=%.3f",
                len(provider_ids),
                perf_counter() - started_at,
            )
            return BriefResult(report=report, articles=[], provider_ids=provider_ids)

        notes = self._summarize_articles(articles, cancellation, on_progress)
        report = self._synthesize_report(notes, articles, cancellation, on_progress)
        report, cited_articles = self._renumber_article_references(report, articles)
        report = self._append_statistics(report, articles, provider_ids)
        self._raise_if_cancelled(cancellation)
        if options.mark_read:
            self._emit(on_progress, 1, 1, "brief.status.marking_read")
            self.mark_sources_read(provider_ids)
        LOGGER.info(
            "brief_generate_done articles=%s cited_articles=%s providers=%s duration_s=%.3f",
            len(articles),
            len(cited_articles),
            len(provider_ids),
            perf_counter() - started_at,
        )
        return BriefResult(report=report, articles=cited_articles, provider_ids=provider_ids)

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

        return [
            self._brief_article(index, article, provider_by_id[article.provider_id])
            for index, article in enumerate(records, start=1)
        ]

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
        batches = self._article_batches(entries, articles, input_budget)
        total = len(batches) + 1
        LOGGER.info(
            "brief_compress_start articles=%s batches=%s input_budget=%s output_tokens=%s",
            len(articles),
            len(batches),
            input_budget,
            output_tokens,
        )
        notes: list[str] = []
        for index, batch in enumerate(batches, start=1):
            self._raise_if_cancelled(cancellation)
            self._emit(
                on_progress,
                index - 1,
                total,
                "brief.status.compressing_summaries",
                index=index,
                total=len(batches),
            )
            batch_started_at = perf_counter()
            LOGGER.info(
                "brief_compress_batch_start batch=%s batches=%s articles=%s source_markers=%s",
                index,
                len(batches),
                len(batch.articles) or len(batch.article_numbers),
                len(batch.article_numbers),
            )
            note = (
                self._llm_client.shorten_brief_notes(
                    prompt,
                    batch.text,
                    max_tokens=output_tokens,
                    cancellation=cancellation,
                )
            )
            LOGGER.info(
                "brief_compress_batch_done batch=%s batches=%s duration_s=%.3f response_chars=%s",
                index,
                len(batches),
                perf_counter() - batch_started_at,
                len(note),
            )
            notes.append(
                self._repair_compressed_notes(
                    note,
                    batch,
                    output_tokens,
                    cancellation,
                    on_progress,
                    batch_index=index,
                    batch_count=len(batches),
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
                self._emit(
                    on_progress,
                    index,
                    len(batches) + 1,
                    "brief.status.reducing_notes",
                    pass_number=iteration,
                )
                trimmed_batch = self._trim_to_budget(batch, input_budget)
                reduce_started_at = perf_counter()
                LOGGER.info(
                    "brief_reduce_batch_start pass=%s batch=%s batches=%s input_budget=%s",
                    iteration,
                    index,
                    len(batches),
                    input_budget,
                )
                note = (
                    self._llm_client.shorten_brief_notes(
                        batch_prompt,
                        trimmed_batch,
                        max_tokens=output_tokens,
                        cancellation=cancellation,
                    )
                )
                LOGGER.info(
                    "brief_reduce_batch_done pass=%s batch=%s batches=%s duration_s=%.3f response_chars=%s",
                    iteration,
                    index,
                    len(batches),
                    perf_counter() - reduce_started_at,
                    len(note),
                )
                batch_scope = frozenset(reference_numbers(trimmed_batch))
                reduced.append(
                    self._repair_compressed_notes(
                        note,
                        _BriefBatch(text=trimmed_batch, article_numbers=batch_scope),
                        output_tokens,
                        cancellation,
                        on_progress,
                        batch_index=index,
                        batch_count=len(batches),
                    )
                )
            if len(reduced) == len(notes) and sum(map(len, reduced)) >= sum(map(len, notes)):
                return [self._trim_to_budget("\n\n".join(reduced), input_budget)]
            notes = reduced
        return [self._trim_to_budget("\n\n".join(notes), input_budget)]

    def _synthesize_report(
        self,
        notes: Sequence[str],
        articles: Sequence[BriefArticle],
        cancellation: RefreshCancellation | None,
        on_progress: ProgressCallback | None,
    ) -> str:
        output_tokens = self._final_output_tokens()
        prompt = self._final_prompt()
        input_budget = self._input_budget(prompt, output_tokens)
        content = self._trim_to_budget("\n\n".join(notes), input_budget)
        self._raise_if_cancelled(cancellation)
        self._emit(on_progress, 1, 1, "brief.status.writing_final")
        started_at = perf_counter()
        LOGGER.info(
            "brief_final_start notes=%s input_budget=%s output_tokens=%s",
            len(notes),
            input_budget,
            output_tokens,
        )
        report = self._llm_client.synthesize_brief_report(
            prompt,
            content,
            max_tokens=output_tokens,
            cancellation=cancellation,
        )
        LOGGER.info(
            "brief_final_done duration_s=%.3f response_chars=%s",
            perf_counter() - started_at,
            len(report),
        )
        return self._repair_report(report, notes, articles, output_tokens, cancellation, on_progress)

    def _repair_compressed_notes(
        self,
        note: str,
        batch: _BriefBatch,
        output_tokens: int,
        cancellation: RefreshCancellation | None,
        on_progress: ProgressCallback | None,
        *,
        batch_index: int,
        batch_count: int,
    ) -> str:
        required_numbers = batch.article_numbers
        validation = validate_brief_text(
            note,
            valid_numbers=required_numbers,
            required_numbers=required_numbers,
        )
        if validation.ok:
            return note

        repaired = note
        self._log_validation("compressed", validation, batch_index=batch_index, batch_count=batch_count)
        for attempt in range(1, MAX_BRIEF_REPAIR_ATTEMPTS + 1):
            self._raise_if_cancelled(cancellation)
            self._emit(
                on_progress,
                max(0, batch_index - 1),
                max(1, batch_count + 1),
                "brief.status.repairing_compressed",
                batch_index=batch_index,
                batch_count=batch_count,
                attempt=attempt,
                attempts=MAX_BRIEF_REPAIR_ATTEMPTS,
            )
            started_at = perf_counter()
            LOGGER.info(
                "brief_repair_compressed_start batch=%s batches=%s attempt=%s attempts=%s",
                batch_index,
                batch_count,
                attempt,
                MAX_BRIEF_REPAIR_ATTEMPTS,
            )
            prompt = self._batch_repair_prompt(required_numbers)
            content = self._repair_content(
                source_text=batch.text,
                draft_text=repaired,
                validation=validation,
                output_tokens=output_tokens,
                prompt=prompt,
            )
            repaired = self._llm_client.shorten_brief_notes(
                prompt,
                content,
                max_tokens=output_tokens,
                cancellation=cancellation,
            )
            LOGGER.info(
                "brief_repair_compressed_done batch=%s batches=%s attempt=%s attempts=%s duration_s=%.3f response_chars=%s",
                batch_index,
                batch_count,
                attempt,
                MAX_BRIEF_REPAIR_ATTEMPTS,
                perf_counter() - started_at,
                len(repaired),
            )
            validation = validate_brief_text(
                repaired,
                valid_numbers=required_numbers,
                required_numbers=required_numbers,
            )
            if validation.ok:
                return repaired
            self._log_validation("compressed", validation, attempt=attempt, batch_index=batch_index, batch_count=batch_count)
        self._emit(
            on_progress,
            max(0, batch_index - 1),
            max(1, batch_count + 1),
            "brief.status.compressed_fallback",
            batch_index=batch_index,
            batch_count=batch_count,
        )
        LOGGER.warning(
            "brief_repair_compressed_fallback batch=%s batches=%s attempts=%s",
            batch_index,
            batch_count,
            MAX_BRIEF_REPAIR_ATTEMPTS,
        )
        return self._fallback_brief_text(repaired, batch.article_numbers, batch.articles)

    def _repair_report(
        self,
        report: str,
        notes: Sequence[str],
        articles: Sequence[BriefArticle],
        output_tokens: int,
        cancellation: RefreshCancellation | None,
        on_progress: ProgressCallback | None,
    ) -> str:
        required_numbers = frozenset(article.number for article in articles)
        validation = validate_brief_text(
            report,
            valid_numbers=required_numbers,
            required_numbers=required_numbers,
        )
        if validation.ok:
            return report

        repaired = report
        self._log_validation("final", validation)
        for attempt in range(1, MAX_BRIEF_REPAIR_ATTEMPTS + 1):
            self._raise_if_cancelled(cancellation)
            self._emit(
                on_progress,
                1,
                1,
                "brief.status.repairing_final",
                attempt=attempt,
                attempts=MAX_BRIEF_REPAIR_ATTEMPTS,
            )
            started_at = perf_counter()
            LOGGER.info(
                "brief_repair_final_start attempt=%s attempts=%s articles=%s",
                attempt,
                MAX_BRIEF_REPAIR_ATTEMPTS,
                len(articles),
            )
            prompt = self._final_repair_prompt(required_numbers)
            content = self._final_repair_content(
                articles=articles,
                notes=notes,
                draft_report=repaired,
                validation=validation,
                output_tokens=output_tokens,
                prompt=prompt,
            )
            repaired = self._llm_client.synthesize_brief_report(
                prompt,
                content,
                max_tokens=output_tokens,
                cancellation=cancellation,
            )
            LOGGER.info(
                "brief_repair_final_done attempt=%s attempts=%s duration_s=%.3f response_chars=%s",
                attempt,
                MAX_BRIEF_REPAIR_ATTEMPTS,
                perf_counter() - started_at,
                len(repaired),
            )
            validation = validate_brief_text(
                repaired,
                valid_numbers=required_numbers,
                required_numbers=required_numbers,
            )
            if validation.ok:
                return repaired
            self._log_validation("final", validation, attempt=attempt)
        self._emit(on_progress, 1, 1, "brief.status.final_fallback")
        LOGGER.warning(
            "brief_repair_final_fallback attempts=%s articles=%s",
            MAX_BRIEF_REPAIR_ATTEMPTS,
            len(articles),
        )
        return self._fallback_brief_text(repaired, required_numbers, articles)

    def _batch_prompt(self) -> str:
        return (
            "Shorten these news summaries into compact brief notes in "
            f"{self._config.translation.target_language}. "
            f"Current local date and time: {self._current_datetime_prompt_value()}. "
            "Keep only distinct important facts. Preserve source markers like [1]. "
            "Return concise Markdown bullets."
        )

    def _final_prompt(self) -> str:
        return (
            f"Markdown brief in {self._config.translation.target_language}: "
            f"Current local date and time: {self._current_datetime_prompt_value()}. "
            "# title; ## topic sections separated by ---; bullets per topic. "
            "Group related items, remove repetition, preserve source markers like [1]."
        )

    def _batch_repair_prompt(self, required_numbers: frozenset[int]) -> str:
        return (
            f"Repair brief notes in {self._config.translation.target_language}. "
            f"Time: {self._current_datetime_prompt_value()}. "
            f"Use only these markers and cite each once: {format_numbers(required_numbers)}. "
            "Every fact line needs a marker. Remove unsupported or invalid facts. Return bullets only."
        )

    def _final_repair_prompt(self, required_numbers: frozenset[int]) -> str:
        return (
            f"Repair Markdown brief in {self._config.translation.target_language}. "
            f"Time: {self._current_datetime_prompt_value()}. "
            f"Use only these markers and cite each once: {format_numbers(required_numbers)}. "
            "Every fact line needs a marker. Remove unsupported or invalid facts. Return brief only."
        )

    def _current_datetime_prompt_value(self) -> str:
        if self._current_time is None:
            return current_datetime_prompt_value()
        return current_datetime_prompt_value(self._current_time())

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

    def _format_article(self, article: BriefArticle, input_budget: int) -> str:
        timestamp = article.published_at or article.created_at
        prefix = (
            f"Source: [{article.number}]\n"
            f"Provider: {article.provider_name}\n"
            f"Title: {article.title}\n"
            f"Published: {timestamp.astimezone().strftime('%Y-%m-%d %H:%M %Z')}\n"
            "Summary:\n"
        )
        remaining = max(1, input_budget - estimate_token_count(prefix) - 1)
        return prefix + self._trim_to_budget(article.summary, remaining)

    def _format_fallback_article(self, article: BriefArticle, input_budget: int) -> str:
        summary = self._trim_to_budget(article.summary, input_budget)
        return f"- {article.title}: {summary} [{article.number}]"

    def _format_source_catalog(self, articles: Sequence[BriefArticle], input_budget: int) -> str:
        entries: list[str] = []
        for article in articles:
            entry = self._format_article(article, max(1, input_budget // max(1, len(articles))))
            entries.append(entry)
        return self._trim_to_budget("\n\n".join(entries), input_budget)

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

    def _article_batches(
        self,
        values: Sequence[str],
        articles: Sequence[BriefArticle],
        input_budget: int,
    ) -> list[_BriefBatch]:
        batches: list[_BriefBatch] = []
        current: list[str] = []
        current_articles: list[BriefArticle] = []
        current_numbers: set[int] = set()
        current_tokens = 0
        for value, article in zip(values, articles, strict=True):
            text = self._trim_to_budget(value, input_budget)
            token_count = estimate_token_count(text)
            separator_tokens = 1 if current else 0
            if current and current_tokens + separator_tokens + token_count > input_budget:
                batches.append(
                    _BriefBatch(
                        text="\n\n".join(current),
                        article_numbers=frozenset(current_numbers),
                        articles=tuple(current_articles),
                    )
                )
                current = []
                current_articles = []
                current_numbers = set()
                current_tokens = 0
                separator_tokens = 0
            current.append(text)
            current_articles.append(article)
            current_numbers.add(article.number)
            current_tokens += token_count + separator_tokens
        if current:
            batches.append(
                _BriefBatch(
                    text="\n\n".join(current),
                    article_numbers=frozenset(current_numbers),
                    articles=tuple(current_articles),
                )
            )
        return batches

    def _repair_content(
        self,
        *,
        source_text: str,
        draft_text: str,
        validation: BriefValidation,
        output_tokens: int,
        prompt: str,
    ) -> str:
        content = (
            f"Source material:\n{source_text}\n\n"
            f"Draft notes:\n{draft_text}\n\n"
            f"Validation problems:\n{format_validation(validation)}"
        )
        return self._trim_to_budget(content, self._input_budget(prompt, output_tokens))

    def _final_repair_content(
        self,
        *,
        articles: Sequence[BriefArticle],
        notes: Sequence[str],
        draft_report: str,
        validation: BriefValidation,
        output_tokens: int,
        prompt: str,
    ) -> str:
        input_budget = self._input_budget(prompt, output_tokens)
        source_budget = max(1, input_budget // 2)
        source_catalog = self._format_source_catalog(articles, source_budget)
        content = (
            f"Source articles:\n{source_catalog}\n\n"
            f"Compressed notes:\n{self._trim_to_budget(chr(10).join(notes), max(1, input_budget // 5))}\n\n"
            f"Draft brief:\n{draft_report}\n\n"
            f"Validation problems:\n{format_validation(validation)}"
        )
        return self._trim_to_budget(content, input_budget)

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

    def _fallback_brief_text(
        self,
        text: str,
        required_numbers: frozenset[int],
        articles: Sequence[BriefArticle],
    ) -> str:
        sanitized = remove_unreferenced_statement_lines(
            remove_invalid_references(text, required_numbers),
            required_numbers,
        ).strip()
        cited_numbers = reference_numbers(sanitized) & required_numbers
        missing_numbers = sorted(required_numbers - cited_numbers)
        if not missing_numbers:
            return sanitized

        fallback_lines = self._fallback_lines(missing_numbers, articles)
        if not fallback_lines:
            return sanitized

        if sanitized:
            return f"{sanitized}\n\n## Additional articles\n\n" + "\n".join(fallback_lines)
        return "# Brief\n\n" + "\n".join(fallback_lines)

    def _fallback_lines(
        self,
        missing_numbers: Sequence[int],
        articles: Sequence[BriefArticle],
    ) -> list[str]:
        articles_by_number = {article.number: article for article in articles}
        lines: list[str] = []
        for number in missing_numbers:
            article = articles_by_number.get(number)
            if article is None:
                lines.append(f"- Source [{number}]")
                continue
            lines.append(self._format_fallback_article(article, 80))
        return lines

    @staticmethod
    def _renumber_article_references(
        report: str,
        articles: Sequence[BriefArticle],
    ) -> tuple[str, list[BriefArticle]]:
        if not articles:
            return report, []

        articles_by_number = {article.number: article for article in articles}
        display_by_source_number: dict[int, int] = {}
        cited_articles: list[BriefArticle] = []
        next_display_number = 1

        def replace_reference(match: re.Match[str]) -> str:
            nonlocal next_display_number

            source_number = int(match.group("number"))
            article = articles_by_number.get(source_number)
            if article is None:
                return match.group(0)

            display_number = display_by_source_number.get(source_number)
            if display_number is None:
                display_number = next_display_number
                display_by_source_number[source_number] = display_number
                cited_articles.append(BriefService._renumber_article(article, display_number))
                next_display_number += 1
            return f"[{display_number}]"

        return SOURCE_REF_RE.sub(replace_reference, report), cited_articles

    @staticmethod
    def _renumber_article(article: BriefArticle, number: int) -> BriefArticle:
        return BriefArticle(
            number=number,
            article_id=article.article_id,
            provider_id=article.provider_id,
            provider_name=article.provider_name,
            title=article.title,
            summary=article.summary,
            published_at=article.published_at,
            created_at=article.created_at,
        )

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
    def _emit(
        callback: ProgressCallback | None,
        completed: int,
        progress_total: int,
        message_key: str,
        **message_args: object,
    ) -> None:
        LOGGER.info(
            "brief_progress completed=%s total=%s message_key=%r message_args=%r",
            completed,
            max(1, progress_total),
            message_key,
            message_args,
        )
        if callback is not None:
            callback(
                BriefProgress(
                    completed=completed,
                    total=max(1, progress_total),
                    message_key=message_key,
                    message_args=dict(message_args),
                )
            )

    @staticmethod
    def _raise_if_cancelled(cancellation: RefreshCancellation | None) -> None:
        if cancellation is not None:
            cancellation.raise_if_cancelled()

    @staticmethod
    def _log_validation(
        stage: str,
        validation: BriefValidation,
        *,
        attempt: int | None = None,
        batch_index: int | None = None,
        batch_count: int | None = None,
    ) -> None:
        LOGGER.warning(
            "brief_validation_failed stage=%s attempt=%s batch=%s batches=%s invalid=%s missing=%s unreferenced=%s",
            stage,
            attempt,
            batch_index,
            batch_count,
            len(validation.invalid_numbers),
            len(validation.missing_numbers),
            len(validation.unreferenced_lines),
        )


def estimate_token_count(value: str) -> int:
    return max(1, (len(value.encode("utf-8")) + 2) // 3)
