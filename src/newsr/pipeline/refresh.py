from __future__ import annotations

import logging
import re
from threading import Lock

from ..cancellation import RefreshCancellation, RefreshCancelled
from ..config.models import AppConfig
from ..domain import ProviderTarget, SectionCandidate
from ..providers.base import NewsProvider
from ..providers.llm.client import OpenAILLMClient
from ..storage.facade import NewsStorage
from .types import ArticleReadyCallback, RefreshProgress, RefreshResult, StatusCallback


_LOG = logging.getLogger("newsr.llm")


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
        on_status: StatusCallback | None = None,
        on_article_ready: ArticleReadyCallback | None = None,
        cancellation: RefreshCancellation | None = None,
    ) -> RefreshResult:
        if not self._refresh_lock.acquire(blocking=False):
            self._emit(on_status, "refresh already running")
            return RefreshResult(new_articles=0, failed_articles=0)

        new_articles = 0
        failed_articles = 0
        pending_candidates: list[SectionCandidate] = []
        try:
            try:
                for provider_record in self.storage.list_enabled_providers():
                    provider = self.providers.get(provider_record.provider_id)
                    if provider is None:
                        failed_articles += 1
                        self._emit(on_status, f"missing provider {provider_record.provider_id}")
                        continue
                    selected_targets = self.storage.list_selected_targets(provider_record.provider_id)
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
            except RefreshCancelled:
                self._emit(on_status, "refresh cancelled")
                return RefreshResult(new_articles=new_articles, failed_articles=failed_articles)
            progress = RefreshProgress(completed_articles=0, total_articles=len(pending_candidates))
            for candidate in pending_candidates:
                self._raise_if_cancelled(cancellation)
                try:
                    self._emit(on_status, f"extracting {candidate.article_id}")
                    provider = self.providers[candidate.provider_id]
                    content = provider.fetch_article(candidate, cancellation)
                    content.body = self._validated_source_text(content.title, content.body)
                    self._raise_if_cancelled(cancellation)
                    self.storage.upsert_article_source(content)
                    self.storage.set_job_status(candidate.article_id, "fetch", "done")
                    if self._process_article_llm(
                        content.article_id,
                        content.title,
                        content.body,
                        on_status,
                        on_article_ready,
                        progress,
                        cancellation,
                    ):
                        new_articles += 1
                    else:
                        failed_articles += 1
                except RefreshCancelled:
                    self._emit(on_status, "refresh cancelled")
                    return RefreshResult(new_articles=new_articles, failed_articles=failed_articles)
                except Exception as exc:
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
            self._emit(on_status, "ready")
            return RefreshResult(new_articles=new_articles, failed_articles=failed_articles)
        finally:
            self._refresh_lock.release()

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
        except RefreshCancelled:
            self.storage.reset_translation(article_id)
            raise
        except Exception as exc:
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
        except RefreshCancelled:
            self.storage.reset_summary(article_id)
            raise
        except Exception as exc:
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
