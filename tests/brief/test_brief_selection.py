from __future__ import annotations

from datetime import UTC, datetime, timedelta

from newsr.brief import BriefOptions, BriefPeriod, BriefService
from newsr.config import AppConfig
from newsr.domain import ArticleContent, ProviderRecord, ReaderState, ViewMode
from newsr.storage import NewsStorage

from tests.brief.support import FakeBriefLLM, seed_article


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
    llm = FakeBriefLLM(report="# Brief\n\nOld [1]\n\nNew [2]")
    service = BriefService(app_config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=True),
        now=now,
    )

    assert [article.article_id for article in result.articles] == ["bbc:old", "bbc:new"]
    assert [article.number for article in result.articles] == [1, 2]
    assert result.provider_ids == ["bbc"]
    assert storage.load_reader_state("bbc").article_id == "bbc:new"
    assert storage.load_reader_state(topic.provider_id).article_id is None
    assert storage.load_reader_state("[ALL]").article_id is None


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
    service = BriefService(app_config, storage, FakeBriefLLM(report="# Brief\n\nNew [1]"))

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
    storage.save_reader_state(
        "bbc",
        ReaderState(article_id=None, view_mode=ViewMode.ORIGINAL, scroll_offset=7),
    )
    storage.save_reader_state(
        "techcrunch",
        ReaderState(article_id=None, view_mode=ViewMode.SUMMARY, scroll_offset=9),
    )
    service = BriefService(app_config, storage, FakeBriefLLM(report="# Brief\n\nNew [1]"))

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=True),
        now=now,
    )

    assert [article.article_id for article in result.articles] == ["techcrunch:new"]
    bbc_state = storage.load_reader_state("bbc")
    assert bbc_state.article_id == "bbc:old"
    assert bbc_state.view_mode == ViewMode.ORIGINAL
    assert bbc_state.scroll_offset == 0
    techcrunch_state = storage.load_reader_state("techcrunch")
    assert techcrunch_state.article_id == "techcrunch:new"
    assert techcrunch_state.view_mode == ViewMode.SUMMARY
    assert techcrunch_state.scroll_offset == 0


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


def test_brief_timed_periods_optionally_filter_unread_articles(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="read-week", minutes_ago=60 * 48, summary="Read week", now=now)
    seed_article(storage, provider_id="bbc", article_id="read-day", minutes_ago=60 * 12, summary="Read day", now=now)
    seed_article(storage, provider_id="bbc", article_id="unread-day", minutes_ago=30, summary="Unread day", now=now)
    seed_article(storage, provider_id="bbc", article_id="unread-old", minutes_ago=60 * 24 * 9, summary="Unread old", now=now)
    storage.save_reader_state("bbc", ReaderState("bbc:read-day", ViewMode.FULL, 0))
    service = BriefService(app_config, storage, FakeBriefLLM())

    def article_ids(period: BriefPeriod, *, only_unread: bool) -> list[str]:
        options = BriefOptions(period=period, only_unread=only_unread)
        return [article.article_id for article in service.select_articles(options, now=now)]

    assert BriefOptions().only_unread is True
    assert article_ids(BriefPeriod.LAST_24H, only_unread=True) == ["bbc:unread-day"]
    assert article_ids(BriefPeriod.LAST_24H, only_unread=False) == ["bbc:read-day", "bbc:unread-day"]
    assert article_ids(BriefPeriod.LAST_WEEK, only_unread=True) == ["bbc:unread-day"]
    assert article_ids(BriefPeriod.LAST_WEEK, only_unread=False) == [
        "bbc:read-week",
        "bbc:read-day",
        "bbc:unread-day",
    ]
    assert article_ids(BriefPeriod.ALL_UNREAD, only_unread=False) == ["bbc:unread-day", "bbc:unread-old"]
