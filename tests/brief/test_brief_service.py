from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from newsr.brief import BriefOptions, BriefPeriod, BriefService, estimate_token_count
from newsr.cancellation import RefreshCancellation
from newsr.config import AppConfig
from newsr.domain import ArticleContent, ProviderRecord, ReaderState, ViewMode
from newsr.storage import NewsStorage


class FakeBriefLLM:
    def __init__(self, *, long_first_pass: bool = False) -> None:
        self.long_first_pass = long_first_pass
        self.shorten_calls: list[tuple[str, str, int]] = []
        self.report_calls: list[tuple[str, str, int]] = []

    def shorten_brief_notes(
        self,
        system_prompt: str,
        notes: str,
        *,
        max_tokens: int,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        self.shorten_calls.append((system_prompt, notes, max_tokens))
        if self.long_first_pass and len(self.shorten_calls) <= 2:
            return "intermediate detail " * 120
        return f"reduced note {len(self.shorten_calls)}"

    def synthesize_brief_report(
        self,
        system_prompt: str,
        notes: str,
        *,
        max_tokens: int,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        self.report_calls.append((system_prompt, notes, max_tokens))
        return "# Brief\n\nFinal report"


def seed_article(
    storage: NewsStorage,
    *,
    provider_id: str,
    article_id: str,
    minutes_ago: int,
    summary: str,
    now: datetime,
) -> None:
    published_at = now - timedelta(minutes=minutes_ago)
    content = ArticleContent(
        article_id=f"{provider_id}:{article_id}",
        provider_id=provider_id,
        provider_article_id=article_id,
        url=f"https://example.com/{provider_id}/{article_id}",
        category="news",
        title=f"Title {article_id}",
        author="Reporter",
        published_at=published_at,
        body=f"Body {article_id}",
    )
    storage.upsert_article_source(content)
    storage.update_translation(content.article_id, f"Translated {article_id}", f"Translated body {article_id}", "done")
    storage.update_summary(content.article_id, summary, "done")


def test_brief_selects_enabled_http_sources_and_marks_real_provider_read(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    topic = storage.create_topic_provider(
        display_name="AI Watch",
        topic_query="AI",
        update_schedule=None,
        enabled=True,
    )
    seed_article(storage, provider_id="bbc", article_id="old", minutes_ago=180, summary="Old summary", now=now)
    seed_article(storage, provider_id="bbc", article_id="new", minutes_ago=30, summary="New summary", now=now)
    seed_article(storage, provider_id=topic.provider_id, article_id="topic", minutes_ago=20, summary="Topic summary", now=now)
    llm = FakeBriefLLM()
    service = BriefService(app_config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=True),
        now=now,
    )

    assert [article.article_id for article in result.articles] == ["bbc:old", "bbc:new"]
    assert result.provider_ids == ["bbc"]
    assert storage.load_reader_state("bbc").article_id == "bbc:new"
    assert storage.load_reader_state(topic.provider_id).article_id is None
    assert storage.load_reader_state("[ALL]").article_id is None


def test_brief_appends_article_counts_for_contributing_providers(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    storage.sync_providers(
        [
            ProviderRecord(
                provider_id="bbc",
                display_name="BBC News",
                enabled=True,
                provider_type="http",
            ),
            ProviderRecord(
                provider_id="techcrunch",
                display_name="TechCrunch",
                enabled=True,
                provider_type="http",
            ),
            ProviderRecord(
                provider_id="infoq",
                display_name="InfoQ",
                enabled=True,
                provider_type="http",
            ),
        ]
    )
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="BBC summary 1", now=now)
    seed_article(storage, provider_id="bbc", article_id="two", minutes_ago=20, summary="BBC summary 2", now=now)
    seed_article(storage, provider_id="techcrunch", article_id="one", minutes_ago=30, summary="TC summary", now=now)
    llm = FakeBriefLLM()
    service = BriefService(app_config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    assert result.report == "# Brief\n\nFinal report\n\n## Statistics\n\nBBC News: 2\n\nTechCrunch: 1"
    assert "Statistics" not in llm.report_calls[0][1]


def test_brief_marks_selected_sources_read_even_without_articles_in_period(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    topic = storage.create_topic_provider(
        display_name="AI Watch",
        topic_query="AI",
        update_schedule=None,
        enabled=True,
    )
    seed_article(storage, provider_id="bbc", article_id="older-1", minutes_ago=60 * 48, summary="Older summary", now=now)
    seed_article(storage, provider_id="bbc", article_id="older-2", minutes_ago=60 * 47, summary="Latest old summary", now=now)
    seed_article(storage, provider_id=topic.provider_id, article_id="topic", minutes_ago=20, summary="Topic summary", now=now)
    service = BriefService(app_config, storage, FakeBriefLLM())

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=True),
        now=now,
    )

    assert result.articles == []
    assert result.report == "# Brief\n\nNo completed article summaries were found for last 24 hours."
    assert storage.load_reader_state("bbc").article_id == "bbc:older-2"
    assert storage.load_reader_state(topic.provider_id).article_id is None
    assert storage.load_reader_state("[ALL]").article_id is None


def test_brief_marks_all_selected_sources_read_not_only_sources_in_report(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    storage.sync_providers(
        [
            ProviderRecord(provider_id="bbc", display_name="BBC News", enabled=True, provider_type="http"),
            ProviderRecord(provider_id="techcrunch", display_name="TechCrunch", enabled=True, provider_type="http"),
        ]
    )
    seed_article(storage, provider_id="bbc", article_id="old", minutes_ago=60 * 48, summary="Old summary", now=now)
    seed_article(
        storage,
        provider_id="techcrunch",
        article_id="new",
        minutes_ago=30,
        summary="New summary",
        now=now,
    )
    service = BriefService(app_config, storage, FakeBriefLLM())

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=True),
        now=now,
    )

    assert [article.article_id for article in result.articles] == ["techcrunch:new"]
    assert storage.load_reader_state("bbc").article_id == "bbc:old"
    assert storage.load_reader_state("techcrunch").article_id == "techcrunch:new"


def test_brief_all_unread_uses_provider_reader_state_without_all_virtual(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="read", minutes_ago=60, summary="Read summary", now=now)
    pending = ArticleContent(
        article_id="bbc:pending",
        provider_id="bbc",
        provider_article_id="pending",
        url="https://example.com/bbc/pending",
        category="news",
        title="Pending summary",
        author="Reporter",
        published_at=now - timedelta(minutes=45),
        body="Pending body",
    )
    storage.upsert_article_source(pending)
    storage.update_translation(pending.article_id, "Pending summary", "Pending body", "done")
    seed_article(storage, provider_id="bbc", article_id="unread", minutes_ago=30, summary="Unread summary", now=now)
    storage.save_reader_state("bbc", ReaderState("bbc:pending", ViewMode.FULL, 0))
    storage.save_reader_state("[ALL]", ReaderState("bbc:unread", ViewMode.FULL, 0))
    service = BriefService(app_config, storage, FakeBriefLLM())

    selected = service.select_articles(
        BriefOptions(period=BriefPeriod.ALL_UNREAD, include_topics=False, mark_read=False),
        now=now,
    )

    assert [article.article_id for article in selected] == ["bbc:unread"]


def test_brief_context_limit_reduces_notes_until_final_request_fits(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    config = replace(app_config, llm=replace(app_config.llm, brief_context=180))
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    for index in range(6):
        seed_article(
            storage,
            provider_id="bbc",
            article_id=f"item-{index}",
            minutes_ago=index,
            summary=("Summary detail " * 20) + str(index),
            now=now,
        )
    llm = FakeBriefLLM(long_first_pass=True)
    service = BriefService(config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    assert result.report == "# Brief\n\nFinal report\n\n## Statistics\n\nBBC News: 6"
    assert len(llm.shorten_calls) > 2
    assert len(llm.report_calls) == 1
    for system_prompt, content, max_tokens in [*llm.shorten_calls, *llm.report_calls]:
        assert estimate_token_count(system_prompt) + estimate_token_count(content) + max_tokens <= config.llm.brief_context
