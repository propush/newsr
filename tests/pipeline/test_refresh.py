from __future__ import annotations

from threading import Event, Thread

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent, ProviderTarget, SectionCandidate
from newsr.pipeline import NewsPipeline


class FakeProvider:
    provider_id = "bbc"
    display_name = "BBC News"

    def default_targets(self) -> list[ProviderTarget]:
        raise AssertionError("default_targets is not used in pipeline tests")

    def discover_targets(
        self, cancellation: RefreshCancellation | None = None
    ) -> list[ProviderTarget]:
        raise AssertionError("discover_targets is not used in pipeline tests")

    def fetch_candidates(
        self, target: ProviderTarget, limit: int, cancellation: RefreshCancellation | None = None
    ) -> list[SectionCandidate]:
        category = target.payload.get("slug", target.target_key)
        return [
            SectionCandidate(
                article_id=f"bbc:{category}-1",
                provider_id="bbc",
                provider_article_id=f"{category}-1",
                url=f"https://www.bbc.com/news/{category}-1",
                category=category,
            )
        ]

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        return ArticleContent(
            article_id=candidate.article_id,
            provider_id=candidate.provider_id,
            provider_article_id=candidate.provider_article_id,
            url=candidate.url,
            category=candidate.category,
            title=f"{candidate.category} article",
            author="Reporter",
            published_at=None,
            body="source body",
        )


class FakeLLM:
    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        return f"translated {article_title}"

    def translate(
        self,
        article_title: str,
        source_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        return f"translated {source_text}"

    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        return f"summary {translated_text}"


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
    assert {article.translated_body for article in articles} == {"translated source body"}
    assert {article.summary for article in articles} == {"summary translated source body"}


class RecordingLLM:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        self.calls.append(f"translate_title:{article_title}")
        return f"translated {article_title}"

    def translate(
        self,
        article_title: str,
        source_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.calls.append(f"translate:{article_title}")
        return f"translated {source_text}"

    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.calls.append(f"summarize:{article_title}")
        return f"summary {translated_text}"


def test_pipeline_refresh_runs_llm_steps_sequentially(app_config, storage) -> None:
    llm = RecordingLLM()
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, llm)

    result = pipeline.refresh()

    assert result.new_articles == 2
    assert llm.calls == [
        "translate_title:world article",
        "translate:world article",
        "summarize:world article",
        "translate_title:technology article",
        "translate:technology article",
        "summarize:technology article",
    ]


def test_pipeline_refresh_emits_progress_aware_statuses(app_config, storage) -> None:
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FakeLLM())
    statuses: list[str] = []

    result = pipeline.refresh(statuses.append)

    assert result.new_articles == 2
    assert statuses == [
        "fetching BBC News: World",
        "fetching BBC News: Technology",
        "extracting bbc:world-1",
        "translating bbc:world-1, done 0 of 2",
        "summarizing bbc:world-1, done 0 of 2",
        "extracting bbc:technology-1",
        "translating bbc:technology-1, done 1 of 2",
        "summarizing bbc:technology-1, done 1 of 2",
        "ready",
    ]


def test_pipeline_refresh_excludes_cached_articles_from_progress_total(
    app_config, storage
) -> None:
    storage.upsert_article_source(
        ArticleContent(
            article_id="bbc:world-1",
            provider_id="bbc",
            provider_article_id="world-1",
            url="https://www.bbc.com/news/world-1",
            category="world",
            title="world article",
            author="Reporter",
            published_at=None,
            body="source body",
        )
    )
    storage.complete_translation("bbc:world-1", "translated world article", "translated source body")
    storage.complete_summary("bbc:world-1", "summary translated source body")
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FakeLLM())
    statuses: list[str] = []

    result = pipeline.refresh(statuses.append)

    assert result.new_articles == 1
    assert statuses == [
        "fetching BBC News: World",
        "fetching BBC News: Technology",
        "extracting bbc:technology-1",
        "translating bbc:technology-1, done 0 of 1",
        "summarizing bbc:technology-1, done 0 of 1",
        "ready",
    ]


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
    assert job is not None
    assert job["status"] == "failed"
    assert job["error_text"] == "article body only repeats the title"


class BlockingLLM:
    def __init__(self) -> None:
        self.translation_started = Event()
        self.release_translation = Event()
        self.translation_calls = 0

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
    assert llm.translation_started.wait(timeout=5)

    second = pipeline.refresh(second_statuses.append)

    llm.release_translation.set()
    thread.join(timeout=5)

    assert len(first_result) == 1
    assert second.new_articles == 0
    assert second.failed_articles == 0
    assert second_statuses == ["refresh already running"]
    assert llm.translation_calls == 2


class BlockingSummaryLLM:
    def __init__(self) -> None:
        self.summary_started = Event()
        self.release_summary = Event()

    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        return f"translated {article_title}"

    def translate(
        self,
        article_title: str,
        source_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        return f"translated {source_text}"

    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.summary_started.set()
        self.release_summary.wait(timeout=5)
        return f"summary {translated_text}"


def test_pipeline_refresh_emits_article_ready_after_translation_before_summary(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    llm = BlockingSummaryLLM()
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, llm)
    ready_article_ids: list[str] = []
    result: list[object] = []

    def run_refresh() -> None:
        result.append(pipeline.refresh(on_article_ready=ready_article_ids.append))

    thread = Thread(target=run_refresh)
    thread.start()

    assert llm.summary_started.wait(timeout=5)
    article = storage.get_article("bbc:world-1")

    assert ready_article_ids == ["bbc:world-1"]
    assert article is not None
    assert article.translated_title == "translated world article"
    assert article.translated_body == "translated source body"
    assert article.summary is None

    llm.release_summary.set()
    thread.join(timeout=5)

    assert len(result) == 1


def test_pipeline_refresh_emits_article_ready_after_summary_completion(
    app_config, storage
) -> None:
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FakeLLM())
    ready_article_ids: list[str] = []

    result = pipeline.refresh(on_article_ready=ready_article_ids.append)

    assert result.new_articles == 2
    assert ready_article_ids == [
        "bbc:world-1",
        "bbc:world-1",
        "bbc:technology-1",
        "bbc:technology-1",
    ]


class CancellingProvider(FakeProvider):
    def __init__(self, cancellation: RefreshCancellation) -> None:
        self.cancellation = cancellation

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        assert cancellation is self.cancellation
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
        assert cancellation is self.cancellation
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
        assert cancellation is self.cancellation
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
    assert article.translation_status == "done"
    assert article.translated_body == "translated source body"
    assert article.summary_status == "pending"
    assert article.summary is None
    assert job is not None
    assert job["status"] == "pending"
    assert job["error_text"] is None


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
    assert article.translation_status == "failed"
    assert fetch_job is not None
    assert fetch_job["status"] == "done"
    assert translation_job is not None
    assert translation_job["status"] == "failed"
    assert "LLM unavailable" in translation_job["error_text"]


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
    assert article.translation_status == "done"
    assert article.summary_status == "failed"
    assert summary_job is not None
    assert summary_job["status"] == "failed"
    assert "LLM unavailable" in summary_job["error_text"]


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
