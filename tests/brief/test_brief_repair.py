from __future__ import annotations

import logging
from datetime import UTC, datetime

from newsr.brief import BriefOptions, BriefPeriod, BriefService
from newsr.config import AppConfig
from newsr.storage import NewsStorage

from tests.brief.support import FakeBriefLLM, seed_article


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
    progress: list[tuple[str, dict[str, object]]] = []
    service = BriefService(app_config, storage, llm)

    service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
        on_progress=lambda value: progress.append((value.message_key, value.message_args)),
    )

    assert ("brief.status.selecting_articles", {}) in progress
    assert (
        "brief.status.repairing_compressed",
        {"batch_index": 1, "batch_count": 1, "attempt": 1, "attempts": 5},
    ) in progress


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
    progress: list[tuple[str, dict[str, object]]] = []
    service = BriefService(app_config, storage, llm)

    service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
        on_progress=lambda value: progress.append((value.message_key, value.message_args)),
    )

    assert ("brief.status.writing_final", {}) in progress
    assert (
        "brief.status.repairing_final",
        {"attempt": 1, "attempts": 5},
    ) in progress


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
    progress: list[tuple[str, dict[str, object]]] = []
    service = BriefService(app_config, storage, llm)

    service.generate(
        BriefOptions(period=BriefPeriod.LAST_24H, include_topics=False, mark_read=False),
        now=now,
        on_progress=lambda value: progress.append((value.message_key, value.message_args)),
    )

    assert (
        "brief.status.repairing_final",
        {"attempt": 5, "attempts": 5},
    ) in progress
    assert ("brief.status.final_fallback", {}) in progress


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
