from __future__ import annotations

import logging
import re
from threading import Lock

from ..cancellation import RefreshCancellation, RefreshCancelled, RefreshTimedOut
from ..config.models import AppConfig
from ..domain import ProviderTarget, SectionCandidate
from ..providers.base import NewsProvider
from ..providers.llm.client import OpenAILLMClient
from ..storage.facade import NewsStorage
from .types import ArticleReadyCallback, RefreshProgress, RefreshResult, StatusCallback


_LOG = logging.getLogger("newsr.llm")


class ArticleProcessingTimeout(RuntimeError):
    def __init__(self, stage: str) -> None:
        super().__init__(stage)
        self.stage = stage


class NewsPipeline:
    def __init__(
        self,
        config: AppConfig,
        storage: NewsStorage,
        providers: dict[str, NewsProvider],
        llm_client: OpenAILLMClient,
    ) -> None:
        self.config = config
        self.storage = storage
        self.providers = providers
        self.llm_client = llm_client
        self._refresh_lock = Lock()

    def refresh(
        self,
        provider_ids: list[str] | StatusCallback | None = None,
        *,
        force: bool = False,
        on_status: StatusCallback | None = None,
        on_article_ready: ArticleReadyCallback | None = None,
        cancellation: RefreshCancellation | None = None,
    ) -> RefreshResult:
        if callable(provider_ids) and on_status is None:
            on_status = provider_ids
            provider_ids = None
        if not self._refresh_lock.acquire(blocking=False):
            self._emit(on_status, "refresh already running")
            return RefreshResult(new_articles=0, failed_articles=0, processed_providers=0)

        new_articles = 0
        failed_articles = 0
        processed_providers = 0
        try:
            try:
                provider_records = self._resolve_provider_records(provider_ids, force=force)
                for provider_record in provider_records:
                    provider = self.providers.get(provider_record.provider_id)
                    if provider is None:
                        failed_articles += 1
                        self._emit(on_status, f"missing provider {provider_record.provider_id}")
                        continue
                    if provider_record.provider_type == "all":
                        continue
                    processed_providers += 1
                    self.storage.mark_refresh_started(provider_record.provider_id)
                    try:
                        provider_new, provider_failed = self._refresh_provider(
                            provider_record.provider_id,
                            provider,
                            on_status,
                            on_article_ready,
                            cancellation,
                        )
                    finally:
                        if cancellation is None or not cancellation.is_cancelled:
                            self.storage.mark_refresh_completed(provider_record.provider_id)
                    new_articles += provider_new
                    failed_articles += provider_failed
            except RefreshCancelled:
                self._emit(on_status, "refresh cancelled")
                return RefreshResult(
                    new_articles=new_articles,
                    failed_articles=failed_articles,
                    processed_providers=processed_providers,
                )
            self._emit(on_status, "ready")
            return RefreshResult(
                new_articles=new_articles,
                failed_articles=failed_articles,
                processed_providers=processed_providers,
            )
        finally:
            self._refresh_lock.release()

    def _resolve_provider_records(
        self,
        provider_ids: list[str] | None,
        *,
        force: bool,
    ) -> list:
        if provider_ids is None:
            return [
                provider
                for provider in self.storage.list_enabled_providers()
                if provider.provider_type != "all"
            ]
        resolved = []
        for provider_id in provider_ids:
            provider = self.storage.get_provider(provider_id)
            if provider is None:
                continue
            if provider.provider_type == "all":
                continue
            if not force and not provider.enabled:
                continue
            resolved.append(provider)
        return resolved

    def _refresh_provider(
        self,
        provider_id: str,
        provider: NewsProvider,
        on_status: StatusCallback | None,
        on_article_ready: ArticleReadyCallback | None,
        cancellation: RefreshCancellation | None,
    ) -> tuple[int, int]:
        new_articles = 0
        failed_articles = 0
        pending_candidates: list[SectionCandidate] = []
        selected_targets = self.storage.list_selected_targets(provider_id)
        for target in selected_targets:
            candidates, target_failed = self._fetch_target_candidates(
                provider,
                target,
                on_status,
                cancellation,
            )
            failed_articles += target_failed
            pending_candidates.extend(candidates)
        if not selected_targets:
            self._emit(on_status, f"no targets selected for {provider.display_name}")
        progress = RefreshProgress(completed_articles=0, total_articles=len(pending_candidates))
        for candidate in pending_candidates:
            self._raise_if_cancelled(cancellation)
            article_cancellation = (
                cancellation.child_with_timeout(self.config.articles.timeout)
                if cancellation is not None
                else RefreshCancellation().child_with_timeout(self.config.articles.timeout)
            )
            try:
                self._emit(on_status, f"extracting {candidate.article_id}")
                content = provider.fetch_article(candidate, article_cancellation)
                content.body = self._validated_source_text(content.title, content.body)
                self._raise_if_cancelled(article_cancellation)
                self.storage.upsert_article_source(content)
                self.storage.set_job_status(candidate.article_id, "fetch", "done")
                if self._process_article_llm(
                    content.article_id,
                    content.title,
                    content.body,
                    on_status,
                    on_article_ready,
                    progress,
                    article_cancellation,
                ):
                    new_articles += 1
                else:
                    failed_articles += 1
            except ArticleProcessingTimeout as exc:
                failed_articles += 1
                error_text = f"article processing exceeded {self.config.articles.timeout} seconds"
                _LOG.warning(
                    "article_timed_out article_id=%s stage=%s timeout_s=%s",
                    candidate.article_id,
                    exc.stage,
                    self.config.articles.timeout,
                )
                self.storage.discard_article_permanently(candidate.article_id, exc.stage, error_text)
            except RefreshTimedOut:
                failed_articles += 1
                error_text = f"article processing exceeded {self.config.articles.timeout} seconds"
                _LOG.warning(
                    "article_timed_out article_id=%s stage=fetch timeout_s=%s",
                    candidate.article_id,
                    self.config.articles.timeout,
                )
                self.storage.discard_article_permanently(candidate.article_id, "fetch", error_text)
            except RefreshCancelled:
                self._emit(on_status, "refresh cancelled")
                raise
            except ValueError as exc:
                failed_articles += 1
                _LOG.warning(
                    "fetch_failed_permanent article_id=%s error=%s", candidate.article_id, exc,
                )
                self.storage.set_job_status(
                    candidate.article_id,
                    "fetch",
                    "failed",
                    error_text=str(exc),
                    increment_attempt=True,
                    mark_known=True,
                )
            except Exception as exc:
                if article_cancellation.timed_out:
                    failed_articles += 1
                    error_text = f"article processing exceeded {self.config.articles.timeout} seconds"
                    _LOG.warning(
                        "article_timed_out article_id=%s stage=fetch timeout_s=%s",
                        candidate.article_id,
                        self.config.articles.timeout,
                    )
                    self.storage.discard_article_permanently(candidate.article_id, "fetch", error_text)
                    continue
                failed_articles += 1
                _LOG.warning(
                    "fetch_failed article_id=%s error=%s", candidate.article_id, exc,
                )
                self.storage.set_job_status(
                    candidate.article_id,
                    "fetch",
                    "failed",
                    error_text=str(exc),
                    increment_attempt=True,
                )
            finally:
                article_cancellation.finish()
        return new_articles, failed_articles

    def _fetch_target_candidates(
        self,
        provider: NewsProvider,
        target: ProviderTarget,
        on_status: StatusCallback | None,
        cancellation: RefreshCancellation | None,
    ) -> tuple[list[SectionCandidate], int]:
        self._raise_if_cancelled(cancellation)
        try:
            self._emit(on_status, f"fetching {provider.display_name}: {target.label}")
            candidates = provider.fetch_candidates(
                target,
                self.config.articles.fetch,
                cancellation,
            )
            self._raise_if_cancelled(cancellation)
        except RefreshCancelled:
            self._emit(on_status, "refresh cancelled")
            raise
        except Exception as exc:
            self._emit(on_status, f"failed to fetch {provider.display_name}: {target.label}: {exc}")
            return [], 1
        return (
            [candidate for candidate in candidates if not self.storage.has_article(candidate.article_id)],
            0,
        )

    def _process_article_llm(
        self,
        article_id: str,
        article_title: str,
        source_text: str,
        on_status: StatusCallback | None,
        on_article_ready: ArticleReadyCallback | None,
        progress: RefreshProgress,
        cancellation: RefreshCancellation | None,
    ) -> bool:
        return self._classify_article(
            article_id,
            article_title,
            source_text,
            on_status,
            on_article_ready,
            progress,
            cancellation,
        )

    def _classify_article(
        self,
        article_id: str,
        article_title: str,
        source_text: str,
        on_status: StatusCallback | None,
        on_article_ready: ArticleReadyCallback | None,
        progress: RefreshProgress,
        cancellation: RefreshCancellation | None,
    ) -> bool:
        try:
            self._raise_if_cancelled(cancellation)
            self.storage.set_job_status(article_id, "classification", "running")
            self._emit_stage_status(on_status, "classifying", article_id, progress)
            categories = self.llm_client.classify_article_categories(article_title, source_text, cancellation)
            self._raise_if_cancelled(cancellation)
            self.storage.replace_categories(article_id, categories)
            self.storage.set_job_status(article_id, "classification", "done")
        except RefreshTimedOut as exc:
            raise ArticleProcessingTimeout("classification") from exc
        except RefreshCancelled:
            self.storage.set_job_status(article_id, "classification", "pending")
            raise
        except Exception as exc:
            if cancellation is not None and cancellation.timed_out:
                raise ArticleProcessingTimeout("classification") from exc
            _LOG.warning("classification_failed article_id=%s error=%s", article_id, exc)
            self.storage.set_job_status(
                article_id,
                "classification",
                "failed",
                error_text=str(exc),
                increment_attempt=True,
            )

        return self._translate_article(
            article_id,
            article_title,
            source_text,
            on_status,
            on_article_ready,
            progress,
            cancellation,
        )

    def _translate_article(
        self,
        article_id: str,
        article_title: str,
        source_text: str,
        on_status: StatusCallback | None,
        on_article_ready: ArticleReadyCallback | None,
        progress: RefreshProgress,
        cancellation: RefreshCancellation | None,
    ) -> bool:
        try:
            self._raise_if_cancelled(cancellation)
            self.storage.set_job_status(article_id, "translation", "running")
            self._emit_stage_status(on_status, "translating", article_id, progress)
            translated_title = self.llm_client.translate_title(article_title, cancellation)
            self._raise_if_cancelled(cancellation)
            translated_text = self.llm_client.translate(article_title, source_text, cancellation)
            self._raise_if_cancelled(cancellation)
            self.storage.complete_translation(article_id, translated_title, translated_text)
            self._emit_article_ready(on_article_ready, article_id)
        except RefreshTimedOut as exc:
            raise ArticleProcessingTimeout("translation") from exc
        except RefreshCancelled:
            self.storage.reset_translation(article_id)
            raise
        except Exception as exc:
            if cancellation is not None and cancellation.timed_out:
                raise ArticleProcessingTimeout("translation") from exc
            _LOG.warning("translation_failed article_id=%s error=%s", article_id, exc)
            self.storage.fail_translation(article_id, str(exc))
            return False

        return self._summarize_article(
            article_id,
            article_title,
            translated_text,
            on_status,
            on_article_ready,
            progress,
            cancellation,
        )

    def _summarize_article(
        self,
        article_id: str,
        article_title: str,
        translated_text: str,
        on_status: StatusCallback | None,
        on_article_ready: ArticleReadyCallback | None,
        progress: RefreshProgress,
        cancellation: RefreshCancellation | None,
    ) -> bool:
        try:
            self._raise_if_cancelled(cancellation)
            self.storage.set_job_status(article_id, "summary", "running")
            self._emit_stage_status(on_status, "summarizing", article_id, progress)
            summary = self.llm_client.summarize(article_title, translated_text, cancellation)
            self._raise_if_cancelled(cancellation)
            self.storage.complete_summary(article_id, summary)
            self._emit_article_ready(on_article_ready, article_id)
            progress.completed_articles += 1
            return True
        except RefreshTimedOut as exc:
            raise ArticleProcessingTimeout("summary") from exc
        except RefreshCancelled:
            self.storage.reset_summary(article_id)
            raise
        except Exception as exc:
            if cancellation is not None and cancellation.timed_out:
                raise ArticleProcessingTimeout("summary") from exc
            _LOG.warning("summary_failed article_id=%s error=%s", article_id, exc)
            self.storage.fail_summary(article_id, str(exc))
            return False

    @staticmethod
    def _emit(callback: StatusCallback | None, message: str) -> None:
        if callback is not None:
            callback(message)

    @classmethod
    def _emit_stage_status(
        cls,
        callback: StatusCallback | None,
        stage: str,
        article_id: str,
        progress: RefreshProgress,
    ) -> None:
        cls._emit(
            callback,
            f"{stage} {article_id}, done {progress.completed_articles} of {progress.total_articles}",
        )

    @staticmethod
    def _emit_article_ready(callback: ArticleReadyCallback | None, article_id: str) -> None:
        if callback is not None:
            callback(article_id)

    @staticmethod
    def _raise_if_cancelled(cancellation: RefreshCancellation | None) -> None:
        if cancellation is not None:
            cancellation.raise_if_cancelled()

    @classmethod
    def _validated_source_text(cls, article_title: str, source_text: str) -> str:
        normalized_source_text = source_text.strip()
        if not normalized_source_text:
            raise ValueError("article body is empty")
        if cls._comparable_text(normalized_source_text) == cls._comparable_text(article_title):
            raise ValueError("article body only repeats the title")
        return normalized_source_text

    @staticmethod
    def _comparable_text(value: str) -> str:
        return _NON_ALNUM_PATTERN.sub("", value).casefold()


_NON_ALNUM_PATTERN = re.compile(r"[\W_]+")
