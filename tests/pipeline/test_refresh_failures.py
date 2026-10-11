from __future__ import annotations

import logging
from types import MethodType

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent, ProviderTarget, SectionCandidate
from newsr.pipeline import NewsPipeline
from newsr.providers.llm import OpenAILLMClient

from tests.pipeline.fakes import FakeLLM, FakeProvider, RecordingLLM


class FailingProvider:
    provider_id = "bbc"
    display_name = "BBC News"

    def default_targets(self) -> list[ProviderTarget]:
        raise AssertionError

    def discover_targets(
        self, cancellation: RefreshCancellation | None = None
    ) -> list[ProviderTarget]:
        raise AssertionError

    def fetch_candidates(
        self, target: ProviderTarget, limit: int, cancellation: RefreshCancellation | None = None
    ) -> list[SectionCandidate]:
        raise OSError("network unavailable")

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        raise AssertionError("fetch_article should not be called when fetch_section fails")


def test_pipeline_refresh_continues_when_section_fetch_fails(app_config, storage) -> None:
    pipeline = NewsPipeline(app_config, storage, {"bbc": FailingProvider()}, FakeLLM())

    result = pipeline.refresh()

    assert result.new_articles == 0
    assert result.failed_articles == 2
    assert storage.list_articles() == []


class TitleOnlyBodyProvider(FakeProvider):
    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        article = super().fetch_article(candidate, cancellation)
        article.body = article.title
        return article


def test_pipeline_refresh_rejects_empty_or_title_only_source_text(app_config, storage) -> None:
    storage.set_selected_targets("bbc", ["world"])
    llm = RecordingLLM()
    pipeline = NewsPipeline(app_config, storage, {"bbc": TitleOnlyBodyProvider()}, llm)

    result = pipeline.refresh()
    article = storage.get_article("bbc:world-1")
    job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'fetch'",
        ("bbc:world-1",),
    ).fetchone()

    assert result.new_articles == 0
    assert result.failed_articles == 1
    assert article is None
    assert llm.calls == []
    assert storage.has_article("bbc:world-1") is True
    assert job is not None
    assert job["status"] == "failed"
    assert job["error_text"] == "article body only repeats the title"


class FailingTranslationLLM(FakeLLM):
    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        raise RuntimeError("LLM unavailable")


class FailingSummaryLLM(FakeLLM):
    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        raise RuntimeError("LLM unavailable")


class FailingClassificationLLM(FakeLLM):
    def classify_article_categories(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> tuple[str, ...]:
        raise RuntimeError("LLM unavailable")


def test_pipeline_refresh_translation_failure_counts_as_failed(app_config, storage) -> None:
    storage.set_selected_targets("bbc", ["world"])
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FailingTranslationLLM())

    result = pipeline.refresh()
    article = storage.get_article("bbc:world-1")
    fetch_job = storage.connection.execute(
        "SELECT status FROM jobs WHERE article_id = ? AND job_type = 'fetch'",
        ("bbc:world-1",),
    ).fetchone()
    translation_job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'translation'",
        ("bbc:world-1",),
    ).fetchone()

    assert result.new_articles == 0
    assert result.failed_articles == 1
    assert article is not None
    assert storage.has_article("bbc:world-1") is False
    assert article.translation_status == "failed"
    assert fetch_job is not None
    assert fetch_job["status"] == "done"
    assert translation_job is not None
    assert translation_job["status"] == "failed"
    assert "LLM unavailable" in translation_job["error_text"]


def test_pipeline_refresh_continues_when_classification_fails(app_config, storage) -> None:
    storage.set_selected_targets("bbc", ["world"])
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FailingClassificationLLM())

    result = pipeline.refresh()
    article = storage.get_article("bbc:world-1")
    classification_job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'classification'",
        ("bbc:world-1",),
    ).fetchone()

    assert result.new_articles == 1
    assert result.failed_articles == 0
    assert article is not None
    assert article.categories == ()
    assert article.translation_status == "done"
    assert article.summary_status == "done"
    assert classification_job is not None
    assert classification_job["status"] == "failed"


def test_pipeline_refresh_retries_empty_classification_until_it_gets_a_label(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    llm = OpenAILLMClient(app_config)
    raw_responses = iter(["[]", "[\"SCIENCE\"]", "translated world article", "translated source body", "summary translated source body"])
    llm._chat = MethodType(lambda self, model, system_prompt, content, cancellation=None: next(raw_responses), llm)  # type: ignore[method-assign]
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, llm)

    result = pipeline.refresh()
    article = storage.get_article("bbc:world-1")
    classification_job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'classification'",
        ("bbc:world-1",),
    ).fetchone()

    assert result.new_articles == 1
    assert result.failed_articles == 0
    assert article is not None
    assert article.categories == ("SCIENCE",)
    assert article.translation_status == "done"
    assert article.summary_status == "done"
    assert classification_job is not None
    assert classification_job["status"] == "done"
    assert classification_job["error_text"] in ("", None)


def test_pipeline_refresh_summary_failure_counts_as_failed(app_config, storage) -> None:
    storage.set_selected_targets("bbc", ["world"])
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FailingSummaryLLM())

    result = pipeline.refresh()
    article = storage.get_article("bbc:world-1")
    summary_job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'summary'",
        ("bbc:world-1",),
    ).fetchone()

    assert result.new_articles == 0
    assert result.failed_articles == 1
    assert article is not None
    assert storage.has_article("bbc:world-1") is False
    assert article.translation_status == "done"
    assert article.summary_status == "failed"
    assert summary_job is not None
    assert summary_job["status"] == "failed"
    assert "LLM unavailable" in summary_job["error_text"]


def test_pipeline_refresh_logs_fetch_failure(app_config, storage, caplog) -> None:
    import logging

    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True
    try:
        storage.set_selected_targets("bbc", ["world"])
        pipeline = NewsPipeline(app_config, storage, {"bbc": TitleOnlyBodyProvider()}, FakeLLM())

        with caplog.at_level(logging.WARNING, logger="newsr.llm"):
            pipeline.refresh()

        assert any(
            "fetch_failed" in record.message and "bbc:world-1" in record.message
            for record in caplog.records
        )
    finally:
        logger.propagate = original_propagate
