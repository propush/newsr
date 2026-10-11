from __future__ import annotations

from datetime import UTC, datetime
from threading import Thread

from newsr.domain import ArticleContent


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
