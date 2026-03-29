from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from threading import Thread
from pathlib import Path

from newsr.domain import ArticleContent
from newsr.domain import ProviderRecord, ProviderTarget
from newsr.domain import ReaderState, ViewMode


def test_storage_dedupes_articles(storage, article_content) -> None:
    storage.upsert_article_source(article_content)
    storage.upsert_article_source(article_content)

    articles = storage.list_articles()

    assert len(articles) == 1
    assert articles[0].article_id == article_content.article_id


def test_storage_persists_translated_title(storage, article_content) -> None:
    storage.upsert_article_source(article_content)
    storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    article = storage.get_article(article_content.article_id)

    assert article is not None
    assert article.translated_title == "Translated title"
    assert article.translated_body == "Translated text"


def test_storage_persists_more_info(storage, article_content) -> None:
    storage.upsert_article_source(article_content)
    storage.update_more_info(article_content.article_id, "Background context")

    article = storage.get_article(article_content.article_id)

    assert article is not None
    assert article.more_info == "Background context"


def test_storage_exposes_article_created_at(storage, article_content) -> None:
    storage.upsert_article_source(article_content)

    article = storage.get_article(article_content.article_id)

    assert article is not None
    assert article.created_at.tzinfo is not None


def test_storage_lists_articles_in_insertion_order(storage, article_content) -> None:
    appended_article = ArticleContent(
        article_id="bbc:test-2",
        provider_id="bbc",
        provider_article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Appended title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Appended body",
    )
    storage.upsert_article_source(article_content)
    storage.upsert_article_source(appended_article)

    articles = storage.list_articles()

    assert [article.article_id for article in articles] == [
        article_content.article_id,
        appended_article.article_id,
    ]


def test_storage_reupsert_does_not_move_existing_article_to_end(storage, article_content) -> None:
    appended_article = ArticleContent(
        article_id="bbc:test-2",
        provider_id="bbc",
        provider_article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Appended title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Appended body",
    )
    updated_article = ArticleContent(
        article_id=article_content.article_id,
        provider_id=article_content.provider_id,
        provider_article_id=article_content.provider_article_id,
        url=article_content.url,
        category="science",
        title="Updated title",
        author="Updated reporter",
        published_at=datetime(2026, 3, 26, 12, 0, tzinfo=UTC),
        body="Updated body",
    )

    storage.upsert_article_source(article_content)
    storage.upsert_article_source(appended_article)
    storage.upsert_article_source(updated_article)

    articles = storage.list_articles()

    assert [article.article_id for article in articles] == [
        article_content.article_id,
        appended_article.article_id,
    ]
    assert articles[0].category == "science"
    assert articles[0].title == "Updated title"


def test_storage_persists_reader_state(storage) -> None:
    state = ReaderState(
        article_id="test-1",
        view_mode=ViewMode.SUMMARY,
        scroll_offset=12,
        theme_name="gruvbox",
    )

    storage.save_reader_state(state)
    loaded = storage.load_reader_state()

    assert loaded == state


def test_storage_persists_provider_registry_and_targets(storage) -> None:
    storage.sync_providers(
        [ProviderRecord(provider_id="rss", display_name="RSS", enabled=False)]
    )
    storage.replace_provider_targets(
        "rss",
        [
            ProviderTarget(
                provider_id="rss",
                target_key="hn",
                target_kind="feed",
                label="Hacker News",
                payload={"url": "https://example.com/feed.xml"},
            )
        ],
    )
    storage.set_selected_targets("rss", ["hn"])

    providers = storage.list_providers()
    targets = storage.list_provider_targets("rss")

    assert any(provider.provider_id == "rss" and provider.enabled is False for provider in providers)
    assert targets == [
        ProviderTarget(
            provider_id="rss",
            target_key="hn",
            target_kind="feed",
            label="Hacker News",
            payload={"url": "https://example.com/feed.xml"},
            discovered_at=None,
            selected=True,
        )
    ]


def test_storage_allows_cross_thread_access(storage, article_content) -> None:
    error: BaseException | None = None

    def worker() -> None:
        nonlocal error
        try:
            storage.upsert_article_source(article_content)
            assert storage.has_article(article_content.article_id)
        except BaseException as exc:  # pragma: no cover - assertion surfaces via error
            error = exc

    thread = Thread(target=worker)
    thread.start()
    thread.join()

    assert error is None
    assert storage.get_article(article_content.article_id) is not None


def test_storage_delete_incomplete_articles_removes_partial_rows(storage, article_content) -> None:
    storage.upsert_article_source(article_content)
    storage.set_job_status(article_content.article_id, "translation", "running")
    completed = ArticleContent(
        article_id="bbc:done-1",
        provider_id="bbc",
        provider_article_id="done-1",
        url="https://www.bbc.com/news/done-1",
        category="technology",
        title="Done title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Done body",
    )
    storage.upsert_article_source(completed)
    storage.complete_translation(completed.article_id, "Done translated", "Done translated body")
    storage.complete_summary(completed.article_id, "Done summary")

    storage.delete_incomplete_articles()

    articles = storage.list_articles()
    jobs = storage.connection.execute("SELECT article_id FROM jobs ORDER BY article_id").fetchall()

    assert [article.article_id for article in articles] == ["bbc:done-1"]
    assert [job["article_id"] for job in jobs] == ["bbc:done-1", "bbc:done-1"]


def test_storage_delete_incomplete_articles_preserves_failed_orphan_jobs(storage) -> None:
    storage.set_job_status("bbc:gone-1", "fetch", "failed", error_text="network error", increment_attempt=True)
    storage.set_job_status("bbc:gone-2", "fetch", "running")

    storage.delete_incomplete_articles()

    jobs = storage.connection.execute(
        "SELECT article_id, status FROM jobs ORDER BY article_id"
    ).fetchall()
    assert len(jobs) == 1
    assert jobs[0]["article_id"] == "bbc:gone-1"
    assert jobs[0]["status"] == "failed"
