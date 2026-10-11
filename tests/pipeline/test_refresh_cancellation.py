from __future__ import annotations

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent, SectionCandidate
from newsr.pipeline import NewsPipeline

from tests.pipeline.fakes import FakeLLM, FakeProvider


class CancellingProvider(FakeProvider):
    def __init__(self, cancellation: RefreshCancellation) -> None:
        self.cancellation = cancellation

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        assert cancellation is not None
        article = super().fetch_article(candidate, cancellation)
        self.cancellation.cancel()
        self.cancellation.raise_if_cancelled()
        return article


def test_pipeline_refresh_cancellation_during_fetch_keeps_storage_consistent(app_config, storage) -> None:
    storage.set_selected_targets("bbc", ["world"])
    cancellation = RefreshCancellation()
    pipeline = NewsPipeline(app_config, storage, {"bbc": CancellingProvider(cancellation)}, FakeLLM())

    result = pipeline.refresh(cancellation=cancellation)

    assert result.new_articles == 0
    assert result.failed_articles == 0
    assert storage.list_articles() == []


class CancellingTranslationLLM(FakeLLM):
    def __init__(self, cancellation: RefreshCancellation) -> None:
        self.cancellation = cancellation

    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        assert cancellation is not None
        self.cancellation.cancel()
        self.cancellation.raise_if_cancelled()
        return article_title


def test_pipeline_refresh_cancellation_during_translation_resets_job_to_pending(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    cancellation = RefreshCancellation()
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, CancellingTranslationLLM(cancellation))

    result = pipeline.refresh(cancellation=cancellation)
    article = storage.get_article("bbc:world-1")
    job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'translation'",
        ("bbc:world-1",),
    ).fetchone()

    assert result.new_articles == 0
    assert result.failed_articles == 0
    assert article is not None
    assert storage.has_article("bbc:world-1") is False
    assert article.translation_status == "pending"
    assert article.translated_body is None
    assert job is not None
    assert job["status"] == "pending"
    assert job["error_text"] is None


class CancellingSummaryLLM(FakeLLM):
    def __init__(self, cancellation: RefreshCancellation) -> None:
        self.cancellation = cancellation

    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        assert cancellation is not None
        self.cancellation.cancel()
        self.cancellation.raise_if_cancelled()
        return translated_text


def test_pipeline_refresh_cancellation_during_summary_preserves_translation(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    cancellation = RefreshCancellation()
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, CancellingSummaryLLM(cancellation))

    result = pipeline.refresh(cancellation=cancellation)
    article = storage.get_article("bbc:world-1")
    job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'summary'",
        ("bbc:world-1",),
    ).fetchone()

    assert result.new_articles == 0
    assert result.failed_articles == 0
    assert article is not None
    assert storage.has_article("bbc:world-1") is False
    assert article.translation_status == "done"
    assert article.translated_body == "translated source body"
    assert article.summary_status == "pending"
    assert article.summary is None
    assert job is not None
    assert job["status"] == "pending"
    assert job["error_text"] is None
