from __future__ import annotations

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent, SectionCandidate
from newsr.pipeline import NewsPipeline

from tests.pipeline.fakes import FakeLLM, FakeProvider


class TimeoutFetchProvider(FakeProvider):
    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        assert cancellation is not None
        cancellation.cancel_due_to_timeout()
        cancellation.raise_if_cancelled()
        return super().fetch_article(candidate, cancellation)


class TimeoutClassificationLLM(FakeLLM):
    def classify_article_categories(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> tuple[str, ...]:
        assert cancellation is not None
        cancellation.cancel_due_to_timeout()
        cancellation.raise_if_cancelled()
        return super().classify_article_categories(article_title, article_text, cancellation)


class TimeoutTranslationLLM(FakeLLM):
    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        assert cancellation is not None
        cancellation.cancel_due_to_timeout()
        cancellation.raise_if_cancelled()
        return super().translate_title(article_title, cancellation)


class TimeoutSummaryLLM(FakeLLM):
    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        assert cancellation is not None
        cancellation.cancel_due_to_timeout()
        cancellation.raise_if_cancelled()
        return super().summarize(article_title, translated_text, cancellation)


def test_pipeline_refresh_timeout_during_fetch_discards_article_and_marks_known(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    pipeline = NewsPipeline(app_config, storage, {"bbc": TimeoutFetchProvider()}, FakeLLM())

    result = pipeline.refresh()

    assert result.new_articles == 0
    assert result.failed_articles == 1
    assert storage.get_article("bbc:world-1") is None
    assert storage.has_article("bbc:world-1") is True
    job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'fetch'",
        ("bbc:world-1",),
    ).fetchone()
    assert job is not None
    assert job["status"] == "failed"
    assert "exceeded 180 seconds" in job["error_text"]


def test_pipeline_refresh_timeout_during_classification_discards_article_and_marks_known(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, TimeoutClassificationLLM())

    result = pipeline.refresh()

    assert result.new_articles == 0
    assert result.failed_articles == 1
    assert storage.get_article("bbc:world-1") is None
    assert storage.has_article("bbc:world-1") is True
    job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'classification'",
        ("bbc:world-1",),
    ).fetchone()
    assert job is not None
    assert job["status"] == "failed"
    assert "exceeded 180 seconds" in job["error_text"]


def test_pipeline_refresh_timeout_during_translation_discards_article_and_marks_known(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, TimeoutTranslationLLM())

    result = pipeline.refresh()

    assert result.new_articles == 0
    assert result.failed_articles == 1
    assert storage.get_article("bbc:world-1") is None
    assert storage.has_article("bbc:world-1") is True
    job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'translation'",
        ("bbc:world-1",),
    ).fetchone()
    assert job is not None
    assert job["status"] == "failed"
    assert "exceeded 180 seconds" in job["error_text"]


def test_pipeline_refresh_timeout_during_summary_discards_article_and_marks_known(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, TimeoutSummaryLLM())

    result = pipeline.refresh()

    assert result.new_articles == 0
    assert result.failed_articles == 1
    assert storage.get_article("bbc:world-1") is None
    assert storage.has_article("bbc:world-1") is True
    job = storage.connection.execute(
        "SELECT status, error_text FROM jobs WHERE article_id = ? AND job_type = 'summary'",
        ("bbc:world-1",),
    ).fetchone()
    assert job is not None
    assert job["status"] == "failed"
    assert "exceeded 180 seconds" in job["error_text"]


def test_pipeline_refresh_timeout_marks_article_known_for_later_refreshes(app_config, storage) -> None:
    storage.set_selected_targets("bbc", ["world"])
    first_pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, TimeoutSummaryLLM())

    first_result = first_pipeline.refresh()
    second_result = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FakeLLM()).refresh()

    assert first_result.failed_articles == 1
    assert second_result.new_articles == 0
    assert second_result.failed_articles == 0
    assert storage.get_article("bbc:world-1") is None
