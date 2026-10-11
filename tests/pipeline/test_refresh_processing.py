from __future__ import annotations

from threading import Event, Thread

from newsr.cancellation import RefreshCancellation
from newsr.pipeline import NewsPipeline

from tests.pipeline.fakes import FakeLLM, FakeProvider, RecordingLLM


def test_pipeline_refresh_processes_new_articles(app_config, storage) -> None:
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FakeLLM())

    result = pipeline.refresh()
    articles = storage.list_articles()

    assert result.new_articles == 2
    assert len(articles) == 2
    assert {article.translated_title for article in articles} == {
        "translated world article",
        "translated technology article",
    }
    assert storage.has_article("bbc:world-1") is True
    assert storage.has_article("bbc:technology-1") is True
    assert {article.translated_body for article in articles} == {"translated source body"}
    assert {article.summary for article in articles} == {"summary translated source body"}
    assert {article.categories for article in articles} == {("TECHNOLOGIES",)}


def test_pipeline_refresh_runs_llm_steps_sequentially(app_config, storage) -> None:
    llm = RecordingLLM()
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, llm)

    result = pipeline.refresh()

    assert result.new_articles == 2
    assert llm.calls == [
        "classify:world article",
        "translate_title:world article",
        "translate:world article",
        "summarize:world article",
        "classify:technology article",
        "translate_title:technology article",
        "translate:technology article",
        "summarize:technology article",
    ]


class BlockingLLM:
    def __init__(self) -> None:
        self.classification_started = Event()
        self.release_classification = Event()
        self.translation_started = Event()
        self.release_translation = Event()
        self.classification_calls = 0
        self.translation_calls = 0

    def classify_article_categories(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> tuple[str, ...]:
        self.classification_calls += 1
        self.classification_started.set()
        self.release_classification.wait(timeout=5)
        return ("TECHNOLOGIES",)

    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        self.translation_calls += 1
        self.translation_started.set()
        self.release_translation.wait(timeout=5)
        return f"translated {article_title}"

    def translate(
        self,
        article_title: str,
        source_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.translation_calls += 1
        return f"translated {source_text}"

    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        return f"summary {translated_text}"


def test_pipeline_refresh_ignores_overlapping_calls(app_config, storage) -> None:
    storage.set_selected_targets("bbc", ["world"])
    llm = BlockingLLM()
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, llm)
    first_result: list[object] = []
    second_statuses: list[str] = []

    def run_first() -> None:
        first_result.append(pipeline.refresh())

    thread = Thread(target=run_first)
    thread.start()
    assert llm.classification_started.wait(timeout=5)

    second = pipeline.refresh(second_statuses.append)

    llm.release_classification.set()
    llm.release_translation.set()
    thread.join(timeout=5)

    assert len(first_result) == 1
    assert second.new_articles == 0
    assert second.failed_articles == 0
    assert second_statuses == ["refresh already running"]
    assert llm.classification_calls == 1
    assert llm.translation_calls == 2


def test_pipeline_refresh_tracks_fetch_job_on_success(app_config, storage) -> None:
    storage.set_selected_targets("bbc", ["world"])
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FakeLLM())

    pipeline.refresh()
    fetch_job = storage.connection.execute(
        "SELECT status FROM jobs WHERE article_id = ? AND job_type = 'fetch'",
        ("bbc:world-1",),
    ).fetchone()

    assert fetch_job is not None
    assert fetch_job["status"] == "done"
