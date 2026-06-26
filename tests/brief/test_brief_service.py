from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from newsr.brief import BriefOptions, BriefPeriod, BriefService, estimate_token_count
from newsr.cancellation import RefreshCancellation
from newsr.config import AppConfig
from newsr.domain import ArticleContent, ProviderRecord, ReaderState, ViewMode
from newsr.storage import NewsStorage


class FakeBriefLLM:
    def __init__(
        self,
        *,
        long_first_pass: bool = False,
        report: str | None = None,
        shorten_responses: list[str] | None = None,
        report_responses: list[str] | None = None,
    ) -> None:
        self.long_first_pass = long_first_pass
        self.report = report
        self.shorten_responses = list(shorten_responses or [])
        self.report_responses = list(report_responses or [])
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
        if self.shorten_responses:
            return self.shorten_responses.pop(0)
        if self.long_first_pass and len(self.shorten_calls) <= 2:
            return "\n".join(
                f"- {'intermediate detail ' * 120}[{number}]"
                for number in _source_numbers(notes)
            )
        return "\n".join(f"- reduced note {number} [{number}]" for number in _source_numbers(notes))

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
        if self.report_responses:
            return self.report_responses.pop(0)
        if self.report is not None:
            return self.report
        return "# Brief\n\n" + "\n".join(
            f"- Final report item {number} [{number}]" for number in _source_numbers(notes)
        )


def _source_numbers(value: str) -> list[int]:
    numbers: list[int] = []
    for part in value.split("[")[1:]:
        raw_number = part.split("]", 1)[0]
        if not raw_number.isdigit():
            continue
        number = int(raw_number)
        if number not in numbers:
            numbers.append(number)
    return numbers or [1]


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
    llm = FakeBriefLLM(report="# Brief\n\nTC [3]\n\nBBC [1]\n\nBBC two [2]\n\nAgain [3]")
    service = BriefService(app_config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    assert result.report == (
        "# Brief\n\nTC [1]\n\nBBC [2]\n\nBBC two [3]\n\nAgain [1]\n\n"
        "## Statistics\n\nBBC News: 2\n\nTechCrunch: 1"
    )
    assert [article.article_id for article in result.articles] == ["techcrunch:one", "bbc:one", "bbc:two"]
    assert [article.number for article in result.articles] == [1, 2, 3]
    assert "Source: [1]" in llm.shorten_calls[0][1]
    assert "Preserve source markers like [1]" in llm.shorten_calls[0][0]
    assert "preserve source markers like [1]" in llm.report_calls[0][0]
    assert "Statistics" not in llm.report_calls[0][1]


def test_brief_repairs_compressed_notes_with_out_of_scope_references(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="One summary", now=now)
    seed_article(storage, provider_id="bbc", article_id="two", minutes_ago=20, summary="Two summary", now=now)
    llm = FakeBriefLLM(
        shorten_responses=[
            "- Bad source [99]",
            "- Fixed one [1]\n- Fixed two [2]",
        ],
        report="# Brief\n\nOne [1]\n\nTwo [2]",
    )
    service = BriefService(app_config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    assert [article.article_id for article in result.articles] == ["bbc:one", "bbc:two"]
    assert len(llm.shorten_calls) == 2
    assert "Repair brief notes" in llm.shorten_calls[1][0]
    assert "Invalid source markers: [99]" in llm.shorten_calls[1][1]
    assert "Missing required source markers: [1], [2]" in llm.shorten_calls[1][1]


def test_brief_progress_reports_compressed_note_repair(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="One summary", now=now)
    llm = FakeBriefLLM(
        shorten_responses=[
            "- Bad source [99]",
            "- Fixed one [1]",
        ],
        report="# Brief\n\nOne [1]",
    )
    progress: list[str] = []
    service = BriefService(app_config, storage, llm)

    service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
        on_progress=lambda value: progress.append(value.status),
    )

    assert "selecting articles" in progress
    assert "repairing compressed summary batch 1 of 1, attempt 1 of 5" in progress


def test_brief_repairs_compressed_notes_without_source_markers(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="One summary", now=now)
    llm = FakeBriefLLM(
        shorten_responses=[
            "- Source-free compression",
            "- Fixed one [1]",
        ],
        report="# Brief\n\nOne [1]",
    )
    service = BriefService(app_config, storage, llm)

    service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    assert len(llm.shorten_calls) == 2
    assert "Statements without valid source markers:" in llm.shorten_calls[1][1]
    assert "- Source-free compression" in llm.shorten_calls[1][1]


def test_brief_repairs_final_report_with_invalid_references(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="One summary", now=now)
    seed_article(storage, provider_id="bbc", article_id="two", minutes_ago=20, summary="Two summary", now=now)
    llm = FakeBriefLLM(
        report_responses=[
            "# Brief\n\nOne [1]\n\nBad [99]",
            "# Brief\n\nOne [1]\n\nTwo [2]",
        ]
    )
    service = BriefService(app_config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    assert result.report == "# Brief\n\nOne [1]\n\nTwo [2]\n\n## Statistics\n\nBBC News: 2"
    assert len(llm.report_calls) == 2
    assert "Repair Markdown brief" in llm.report_calls[1][0]
    assert "Invalid source markers: [99]" in llm.report_calls[1][1]


def test_brief_progress_reports_final_report_repair(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="One summary", now=now)
    llm = FakeBriefLLM(
        report_responses=[
            "# Brief\n\nBad [99]",
            "# Brief\n\nOne [1]",
        ]
    )
    progress: list[str] = []
    service = BriefService(app_config, storage, llm)

    service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
        on_progress=lambda value: progress.append(value.status),
    )

    assert "writing final brief" in progress
    assert "repairing final brief, attempt 1 of 5" in progress


def test_brief_repairs_final_report_with_missing_articles(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="One summary", now=now)
    seed_article(storage, provider_id="bbc", article_id="two", minutes_ago=20, summary="Two summary", now=now)
    llm = FakeBriefLLM(
        report_responses=[
            "# Brief\n\nOne [1]",
            "# Brief\n\nOne [1]\n\nTwo [2]",
        ]
    )
    service = BriefService(app_config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    assert [article.article_id for article in result.articles] == ["bbc:one", "bbc:two"]
    assert len(llm.report_calls) == 2
    assert "Missing required source markers: [2]" in llm.report_calls[1][1]


def test_brief_falls_back_after_max_failed_final_repairs(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="One summary", now=now)
    seed_article(storage, provider_id="bbc", article_id="two", minutes_ago=20, summary="Two summary", now=now)
    llm = FakeBriefLLM(
        report_responses=[
            "# Brief\n\nUnsupported line\n\nOne [1]\n\nBad [99]",
            "# Brief\n\nUnsupported line\n\nOne [1]\n\nBad [99]",
            "# Brief\n\nUnsupported line\n\nOne [1]\n\nBad [99]",
            "# Brief\n\nUnsupported line\n\nOne [1]\n\nBad [99]",
            "# Brief\n\nUnsupported line\n\nOne [1]\n\nBad [99]",
            "# Brief\n\nUnsupported line\n\nOne [1]\n\nBad [99]",
        ]
    )
    service = BriefService(app_config, storage, llm)

    result = service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    assert len(llm.report_calls) == 6
    assert "[99]" not in result.report
    assert "Unsupported line" not in result.report
    assert "Bad" not in result.report
    assert "- Translated two: Two summary [2]" in result.report
    assert [article.article_id for article in result.articles] == ["bbc:one", "bbc:two"]


def test_brief_progress_reports_final_fallback_after_failed_repairs(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="One summary", now=now)
    llm = FakeBriefLLM(
        report_responses=[
            "# Brief\n\nBad [99]",
            "# Brief\n\nBad [99]",
            "# Brief\n\nBad [99]",
            "# Brief\n\nBad [99]",
            "# Brief\n\nBad [99]",
            "# Brief\n\nBad [99]",
        ]
    )
    progress: list[str] = []
    service = BriefService(app_config, storage, llm)

    service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
        on_progress=lambda value: progress.append(value.status),
    )

    assert "repairing final brief, attempt 5 of 5" in progress
    assert "using fallback for final brief" in progress


def test_brief_logs_repair_metadata_without_source_text(
    app_config: AppConfig,
    storage: NewsStorage,
    caplog,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    seed_article(
        storage,
        provider_id="bbc",
        article_id="secret",
        minutes_ago=10,
        summary="SECRET_SUMMARY_SHOULD_NOT_BE_LOGGED",
        now=now,
    )
    llm = FakeBriefLLM(
        report_responses=[
            "# Brief\n\nSECRET_REPORT_SHOULD_NOT_BE_LOGGED [99]",
            "# Brief\n\nSecret [1]",
        ]
    )
    logger = logging.getLogger("newsr.llm")
    service = BriefService(app_config, storage, llm)
    original_propagate = logger.propagate

    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="newsr.llm"):
            service.generate(
                BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
                now=now,
            )
    finally:
        logger.propagate = original_propagate

    messages = "\n".join(record.getMessage() for record in caplog.records if record.name == logger.name)
    assert "brief_validation_failed stage=final" in messages
    assert "brief_repair_final_start attempt=1" in messages
    assert "invalid=1" in messages
    assert "SECRET_SUMMARY_SHOULD_NOT_BE_LOGGED" not in messages
    assert "SECRET_REPORT_SHOULD_NOT_BE_LOGGED" not in messages


def test_brief_prompts_include_current_datetime(
    app_config: AppConfig,
    storage: NewsStorage,
) -> None:
    now = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    prompt_time = datetime(2026, 6, 26, 13, 4, 5, tzinfo=UTC)
    seed_article(storage, provider_id="bbc", article_id="one", minutes_ago=10, summary="BBC summary", now=now)
    llm = FakeBriefLLM(report="# Brief\n\nBBC [1]")
    service = BriefService(app_config, storage, llm, current_time=lambda: prompt_time)

    service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
    )

    expected = "Current local date and time: 2026-06-26 13:04:05 UTC."
    assert expected in llm.shorten_calls[0][0]
    assert expected in llm.report_calls[0][0]


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
    service = BriefService(app_config, storage, FakeBriefLLM(report="# Brief\n\nNew [1]"))

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

    assert result.report.startswith("# Brief")
    assert result.report.endswith("## Statistics\n\nBBC News: 6")
    assert [article.article_id for article in result.articles] == [
        "bbc:item-0",
        "bbc:item-1",
        "bbc:item-2",
        "bbc:item-3",
        "bbc:item-4",
        "bbc:item-5",
    ]
    assert len(llm.shorten_calls) > 2
    assert len(llm.report_calls) >= 1
    for system_prompt, content, max_tokens in [*llm.shorten_calls, *llm.report_calls]:
        assert estimate_token_count(system_prompt) + estimate_token_count(content) + max_tokens <= config.llm.brief_context
