from __future__ import annotations

from pathlib import Path
import sqlite3
from datetime import UTC, datetime, timedelta
from threading import Thread

import pytest

from newsr.domain import AppOptions, ArticleContent
from newsr.domain import ProviderRecord, ProviderTarget
from newsr.domain import ReaderState, ViewMode
from newsr.storage import NewsStorage


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


def test_storage_persists_assigned_categories(storage, article_content) -> None:
    storage.upsert_article_source(article_content)
    storage.replace_categories(article_content.article_id, ["SCIENCE", "TECHNOLOGIES"])

    article = storage.get_article(article_content.article_id)

    assert article is not None
    assert article.categories == ("TECHNOLOGIES", "SCIENCE")


def test_storage_replaces_assigned_categories(storage, article_content) -> None:
    storage.upsert_article_source(article_content)
    storage.replace_categories(article_content.article_id, ["SCIENCE", "TECHNOLOGIES"])
    storage.replace_categories(article_content.article_id, ["BUSINESS"])

    article = storage.get_article(article_content.article_id)

    assert article is not None
    assert article.categories == ("BUSINESS",)


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
    all_state = ReaderState(
        article_id="test-1",
        view_mode=ViewMode.SUMMARY,
        scroll_offset=12,
    )
    provider_state = ReaderState(
        article_id="bbc:test-2",
        view_mode=ViewMode.FULL,
        scroll_offset=3,
    )

    storage.save_reader_state("[ALL]", all_state)
    storage.save_reader_state("bbc", provider_state)

    assert storage.load_reader_state("[ALL]") == all_state
    assert storage.load_reader_state("bbc") == provider_state


def test_storage_persists_options(storage) -> None:
    options = AppOptions(theme_name="gruvbox")

    storage.save_options(options)

    assert storage.load_options() == options


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
            storage.complete_summary(article_content.article_id, "Summary")
            assert storage.has_article(article_content.article_id)
        except BaseException as exc:  # pragma: no cover - assertion surfaces via error
            error = exc

    thread = Thread(target=worker)
    thread.start()
    thread.join()

    assert error is None
    assert storage.get_article(article_content.article_id) is not None


def test_storage_persists_article_ids_in_known_duplicates_table(storage, article_content) -> None:
    storage.upsert_article_source(article_content)
    storage.complete_summary(article_content.article_id, "Summary")
    storage.prune_expired(days_to_keep=0)

    assert storage.has_article(article_content.article_id) is True
    assert storage.list_articles() == []


def test_storage_does_not_mark_article_known_on_source_insert(storage, article_content) -> None:
    storage.upsert_article_source(article_content)

    assert storage.has_article(article_content.article_id) is False


def test_storage_creates_topic_provider_with_default_target(storage) -> None:
    provider = storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule="*/15 * * * *",
    )

    stored_provider = storage.get_provider(provider.provider_id)
    targets = storage.list_provider_targets(provider.provider_id)

    assert stored_provider is not None
    assert stored_provider.provider_type == "topic"
    assert stored_provider.update_schedule == "*/15 * * * *"
    assert stored_provider.settings == {"topic_query": "OpenAI policy"}
    assert targets == [
        ProviderTarget(
            provider_id=provider.provider_id,
            target_key="watch",
            target_kind="topic",
            label="OpenAI policy",
            payload={"query": "OpenAI policy"},
            discovered_at=None,
            selected=True,
        )
    ]


def test_storage_lists_due_providers_using_provider_override_and_default_schedule(storage) -> None:
    topic_provider = storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule="*/15 * * * *",
    )
    storage.mark_refresh_completed("bbc")
    storage.mark_refresh_completed(topic_provider.provider_id)
    stale_timestamp = datetime.now(UTC) - timedelta(hours=2)
    storage.connection.execute(
        """
        UPDATE providers
        SET last_refresh_completed_at = ?
        WHERE provider_id = ?
        """,
        (stale_timestamp.isoformat(), "bbc"),
    )
    storage.connection.execute(
        """
        UPDATE providers
        SET last_refresh_completed_at = ?
        WHERE provider_id = ?
        """,
        ((datetime.now(UTC) - timedelta(minutes=20)).isoformat(), topic_provider.provider_id),
    )
    storage.connection.commit()

    due_providers = storage.list_due_providers("0 * * * *")

    assert {provider.provider_id for provider in due_providers} == {"bbc", topic_provider.provider_id}


def test_storage_rejects_duplicate_topic_provider_names_case_insensitively(storage) -> None:
    storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )

    with pytest.raises(ValueError, match="OpenAI policy"):
        storage.create_topic_provider(
            display_name="  openai   policy  ",
            topic_query="  openai   policy  ",
            update_schedule=None,
        )


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


def test_storage_discard_article_permanently_removes_partial_rows_and_marks_known(
    storage,
    article_content,
) -> None:
    storage.upsert_article_source(article_content)
    storage.set_job_status(article_content.article_id, "translation", "running")

    storage.discard_article_permanently(
        article_content.article_id,
        "translation",
        "article processing exceeded 180 seconds",
    )

    assert storage.get_article(article_content.article_id) is None
    assert storage.has_article(article_content.article_id) is True
    jobs = storage.connection.execute(
        "SELECT job_type, status, error_text FROM jobs WHERE article_id = ? ORDER BY job_type",
        (article_content.article_id,),
    ).fetchall()
    assert len(jobs) == 1
    assert jobs[0]["job_type"] == "translation"
    assert jobs[0]["status"] == "failed"
    assert "exceeded 180 seconds" in jobs[0]["error_text"]


def test_storage_migrates_existing_articles_table_to_include_assigned_categories(tmp_path: Path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    connection = sqlite3.connect(storage_path)
    try:
        connection.execute(
            """
            CREATE TABLE articles (
                article_id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                provider_article_id TEXT NOT NULL,
                url TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                translated_title TEXT,
                author TEXT,
                published_at TEXT,
                source_body TEXT NOT NULL,
                translated_body TEXT,
                summary TEXT,
                more_info TEXT,
                translation_status TEXT NOT NULL,
                summary_status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    storage = NewsStorage(storage_path)
    try:
        storage.initialize()
        columns = {
            row["name"]
            for row in storage.connection.execute("PRAGMA table_info(articles)").fetchall()
        }
        assert "assigned_categories_json" in columns
    finally:
        storage.close()


def test_storage_migrates_existing_articles_into_known_article_ids(tmp_path: Path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    connection = sqlite3.connect(storage_path)
    try:
        connection.execute(
            """
            CREATE TABLE articles (
                article_id TEXT PRIMARY KEY,
                provider_id TEXT NOT NULL,
                provider_article_id TEXT NOT NULL,
                url TEXT NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                translated_title TEXT,
                author TEXT,
                published_at TEXT,
                source_body TEXT NOT NULL,
                translated_body TEXT,
                summary TEXT,
                more_info TEXT,
                translation_status TEXT NOT NULL,
                summary_status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO articles (
                article_id, provider_id, provider_article_id, url, category, title,
                translated_title, author, published_at, source_body, translated_body,
                summary, more_info, translation_status, summary_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "bbc:legacy-1",
                "bbc",
                "legacy-1",
                "https://www.bbc.com/news/legacy-1",
                "world",
                "Legacy title",
                None,
                "Reporter",
                None,
                "Legacy body",
                None,
                None,
                None,
                "pending",
                "pending",
                datetime.now(UTC).isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )
        connection.commit()
    finally:
        connection.close()

    storage = NewsStorage(storage_path)
    try:
        storage.initialize()
        rows = storage.connection.execute(
            "SELECT article_id FROM known_article_ids ORDER BY article_id"
        ).fetchall()
        assert [row["article_id"] for row in rows] == ["bbc:legacy-1"]
    finally:
        storage.close()
