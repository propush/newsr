from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from newsr.brief import BriefOptions, BriefPeriod, BriefService, estimate_token_count
from newsr.config import AppConfig
from newsr.domain import ProviderRecord
from newsr.storage import NewsStorage

from tests.brief.support import FakeBriefLLM, seed_article


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
