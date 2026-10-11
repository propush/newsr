from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from time import perf_counter

from ..cancellation import RefreshCancellation
from ..config.models import AppConfig
from ..storage.facade import NewsStorage
from .budget import BriefBudget, trim_to_budget
from .formatting import article_batches, batch_texts, final_repair_content, format_article, repair_content
from .models import BriefArticle, BriefBatch, BriefOptions, BriefResult, Clock, ProgressCallback
from .progress import LOGGER, emit_progress, log_validation, raise_if_cancelled
from .prompts import BriefPrompts
from .repair import MAX_BRIEF_REPAIR_ATTEMPTS, reference_numbers, validate_brief_text
from .report import append_statistics, empty_report, fallback_brief_text, renumber_article_references
from .selection import BriefArticleSelector


class BriefService:
    def __init__(
        self,
        config: AppConfig,
        storage: NewsStorage,
        llm_client,
        *,
        current_time: Clock | None = None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._llm_client = llm_client
        self._selector = BriefArticleSelector(storage)
        self._prompts = BriefPrompts(config.translation.target_language, current_time)
        self._budget = BriefBudget(config.llm.brief_context)

    def generate(
        self,
        options: BriefOptions,
        *,
        now: datetime | None = None,
        cancellation: RefreshCancellation | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BriefResult:
        started_at = perf_counter()
        raise_if_cancelled(cancellation)
        emit_progress(on_progress, 0, 1, "brief.status.selecting_articles")
        articles = self.select_articles(options, now=now)
        provider_ids = self._selector.selected_provider_ids(options)
        LOGGER.info(
            "brief_generate_start period=%s include_topics=%s mark_read=%s only_unread=%s articles=%s providers=%s",
            options.period,
            options.include_topics,
            options.mark_read,
            options.only_unread,
            len(articles),
            len(provider_ids),
        )
        if not articles:
            report = empty_report(options)
            if options.mark_read:
                emit_progress(on_progress, 0, 1, "brief.status.marking_read")
                self.mark_sources_read(provider_ids)
            LOGGER.info(
                "brief_generate_done articles=0 providers=%s duration_s=%.3f",
                len(provider_ids),
                perf_counter() - started_at,
            )
            return BriefResult(report=report, articles=[], provider_ids=provider_ids)

        notes = self._summarize_articles(articles, cancellation, on_progress)
        report = self._synthesize_report(notes, articles, cancellation, on_progress)
        report, cited_articles = renumber_article_references(report, articles)
        report = append_statistics(report, articles, provider_ids)
        raise_if_cancelled(cancellation)
        if options.mark_read:
            emit_progress(on_progress, 1, 1, "brief.status.marking_read")
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
        return self._selector.select_articles(options, now=now)

    def mark_articles_read(self, articles: Sequence[BriefArticle]) -> None:
        self._selector.mark_articles_read(articles)

    def mark_sources_read(self, provider_ids: Sequence[str]) -> None:
        self._selector.mark_sources_read(provider_ids)

    def _summarize_articles(
        self,
        articles: Sequence[BriefArticle],
        cancellation: RefreshCancellation | None,
        on_progress: ProgressCallback | None,
    ) -> list[str]:
        output_tokens = self._budget.batch_output_tokens()
        prompt = self._prompts.batch()
        input_budget = self._budget.input_budget(prompt, output_tokens)
        entries = [format_article(article, input_budget) for article in articles]
        batches = article_batches(entries, articles, input_budget)
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
            raise_if_cancelled(cancellation)
            emit_progress(
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
        output_tokens = self._budget.batch_output_tokens()
        batch_prompt = self._prompts.batch()
        final_prompt = self._prompts.final()
        input_budget = self._budget.input_budget(batch_prompt, output_tokens)
        for iteration in range(1, 21):
            raise_if_cancelled(cancellation)
            if self._budget.fits(final_prompt, "\n\n".join(notes), self._budget.final_output_tokens()):
                return notes
            batches = batch_texts(notes, input_budget)
            reduced: list[str] = []
            for index, batch in enumerate(batches, start=1):
                emit_progress(
                    on_progress,
                    index,
                    len(batches) + 1,
                    "brief.status.reducing_notes",
                    pass_number=iteration,
                )
                trimmed_batch = trim_to_budget(batch, input_budget)
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
                        BriefBatch(text=trimmed_batch, article_numbers=batch_scope),
                        output_tokens,
                        cancellation,
                        on_progress,
                        batch_index=index,
                        batch_count=len(batches),
                    )
                )
            if len(reduced) == len(notes) and sum(map(len, reduced)) >= sum(map(len, notes)):
                return [trim_to_budget("\n\n".join(reduced), input_budget)]
            notes = reduced
        return [trim_to_budget("\n\n".join(notes), input_budget)]

    def _synthesize_report(
        self,
        notes: Sequence[str],
        articles: Sequence[BriefArticle],
        cancellation: RefreshCancellation | None,
        on_progress: ProgressCallback | None,
    ) -> str:
        output_tokens = self._budget.final_output_tokens()
        prompt = self._prompts.final()
        input_budget = self._budget.input_budget(prompt, output_tokens)
        content = trim_to_budget("\n\n".join(notes), input_budget)
        raise_if_cancelled(cancellation)
        emit_progress(on_progress, 1, 1, "brief.status.writing_final")
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
        batch: BriefBatch,
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
        log_validation("compressed", validation, batch_index=batch_index, batch_count=batch_count)
        for attempt in range(1, MAX_BRIEF_REPAIR_ATTEMPTS + 1):
            raise_if_cancelled(cancellation)
            emit_progress(
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
            prompt = self._prompts.batch_repair(required_numbers)
            content = repair_content(
                source_text=batch.text,
                draft_text=repaired,
                validation=validation,
                input_budget=self._budget.input_budget(prompt, output_tokens),
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
            log_validation("compressed", validation, attempt=attempt, batch_index=batch_index, batch_count=batch_count)
        emit_progress(
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
        return fallback_brief_text(repaired, batch.article_numbers, batch.articles)

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
        log_validation("final", validation)
        for attempt in range(1, MAX_BRIEF_REPAIR_ATTEMPTS + 1):
            raise_if_cancelled(cancellation)
            emit_progress(
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
            prompt = self._prompts.final_repair(required_numbers)
            content = final_repair_content(
                articles=articles,
                notes=notes,
                draft_report=repaired,
                validation=validation,
                input_budget=self._budget.input_budget(prompt, output_tokens),
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
            log_validation("final", validation, attempt=attempt)
        emit_progress(on_progress, 1, 1, "brief.status.final_fallback")
        LOGGER.warning(
            "brief_repair_final_fallback attempts=%s articles=%s",
            MAX_BRIEF_REPAIR_ATTEMPTS,
            len(articles),
        )
        return fallback_brief_text(repaired, required_numbers, articles)
