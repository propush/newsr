from __future__ import annotations

from threading import Event, Thread

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent, SectionCandidate
from newsr.pipeline import NewsPipeline
from newsr.providers.base import SkipArticle

from tests.pipeline.fakes import FakeLLM, FakeProvider


def test_pipeline_refresh_emits_progress_aware_statuses(app_config, storage) -> None:
    pipeline = NewsPipeline(app_config, storage, {"bbc": FakeProvider()}, FakeLLM())
    statuses: list[str] = []

    result = pipeline.refresh(statuses.append)

    assert result.new_articles == 2
    assert statuses == [
        "fetching BBC News: World",
        "fetching BBC News: Technology",
        "extracting bbc:world-1",
        "classifying bbc:world-1, done 0 of 2",
        "translating bbc:world-1, done 0 of 2",
        "summarizing bbc:world-1, done 0 of 2",
        "extracting bbc:technology-1",
        "classifying bbc:technology-1, done 1 of 2",
        "translating bbc:technology-1, done 1 of 2",
        "summarizing bbc:technology-1, done 1 of 2",
        "ready",
    ]


class SkipWorldProvider(FakeProvider):
    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        if candidate.category == "world":
            raise SkipArticle("outside configured retention window")
        return super().fetch_article(candidate, cancellation)


def test_pipeline_skipped_article_advances_progress(app_config, storage) -> None:
    pipeline = NewsPipeline(app_config, storage, {"bbc": SkipWorldProvider()}, FakeLLM())
    statuses: list[str] = []

    result = pipeline.refresh(statuses.append)

    assert result.new_articles == 1
    assert result.failed_articles == 0
    assert "classifying bbc:technology-1, done 1 of 2" in statuses


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
        "classifying bbc:technology-1, done 0 of 1",
        "translating bbc:technology-1, done 0 of 1",
        "summarizing bbc:technology-1, done 0 of 1",
        "ready",
    ]


class BlockingSummaryLLM:
    def __init__(self) -> None:
        self.summary_started = Event()
        self.release_summary = Event()

    def classify_article_categories(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> tuple[str, ...]:
        return ("TECHNOLOGIES",)

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
    assert article.categories == ("TECHNOLOGIES",)
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
