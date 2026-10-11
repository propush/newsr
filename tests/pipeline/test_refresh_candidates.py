from __future__ import annotations

import logging

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent, ProviderTarget, SectionCandidate
from newsr.pipeline import NewsPipeline
from newsr.providers.base import SkipArticle

from tests.pipeline.fakes import FakeProvider, RecordingLLM


class SkippingProvider(FakeProvider):
    def __init__(self) -> None:
        self.fetch_article_calls = 0

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        self.fetch_article_calls += 1
        raise SkipArticle("outside configured retention window")


def test_pipeline_remembers_skipped_articles_without_counting_failures(
    app_config, storage
) -> None:
    storage.set_selected_targets("bbc", ["world"])
    provider = SkippingProvider()
    llm = RecordingLLM()
    pipeline = NewsPipeline(app_config, storage, {"bbc": provider}, llm)

    first_result = pipeline.refresh()
    second_result = pipeline.refresh()

    assert first_result.new_articles == 0
    assert first_result.failed_articles == 0
    assert second_result.new_articles == 0
    assert second_result.failed_articles == 0
    assert provider.fetch_article_calls == 1
    assert llm.calls == []
    assert storage.get_article("bbc:world-1") is None
    assert storage.has_article("bbc:world-1") is True
    assert storage.connection.execute(
        "SELECT COUNT(*) FROM jobs WHERE article_id = ?", ("bbc:world-1",)
    ).fetchone()[0] == 0


class DuplicateCandidateProvider(FakeProvider):
    def __init__(self) -> None:
        self.fetched_article_ids: list[str] = []

    def fetch_candidates(
        self, target: ProviderTarget, limit: int, cancellation: RefreshCancellation | None = None
    ) -> list[SectionCandidate]:
        category = target.payload.get("slug", target.target_key)
        return [
            SectionCandidate(
                article_id="bbc:shared-1",
                provider_id="bbc",
                provider_article_id="shared-1",
                url="https://www.bbc.com/news/shared-1",
                category=category,
            )
        ]

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        self.fetched_article_ids.append(candidate.article_id)
        return super().fetch_article(candidate, cancellation)


def test_pipeline_refresh_deduplicates_candidates_across_targets(
    app_config, storage, caplog
) -> None:
    provider = DuplicateCandidateProvider()
    llm = RecordingLLM()
    pipeline = NewsPipeline(app_config, storage, {"bbc": provider}, llm)
    statuses: list[str] = []
    logger = logging.getLogger("newsr.llm")
    original_propagate = logger.propagate
    logger.propagate = True

    try:
        with caplog.at_level(logging.INFO, logger="newsr.llm"):
            result = pipeline.refresh(statuses.append)
    finally:
        logger.propagate = original_propagate

    articles = storage.list_articles()
    assert result.new_articles == 1
    assert result.failed_articles == 0
    assert provider.fetched_article_ids == ["bbc:shared-1"]
    assert llm.calls == [
        "classify:technology article",
        "translate_title:technology article",
        "translate:technology article",
        "summarize:technology article",
    ]
    assert len(articles) == 1
    assert articles[0].article_id == "bbc:shared-1"
    assert articles[0].category == "technology"
    assert statuses == [
        "fetching BBC News: World",
        "fetching BBC News: Technology",
        "extracting bbc:shared-1",
        "classifying bbc:shared-1, done 0 of 1",
        "translating bbc:shared-1, done 0 of 1",
        "summarizing bbc:shared-1, done 0 of 1",
        "ready",
    ]
    assert (
        "duplicate_candidate_deduplicated provider_id=bbc article_id=bbc:shared-1 "
        "replaced_target_key=world selected_target_key=technology"
    ) in caplog.messages
