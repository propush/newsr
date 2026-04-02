from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

from ..domain import normalize_article_categories
from ..domain.articles import ArticleContent, ArticleRecord
from .connection import StorageConnection


class ArticleStore:
    def __init__(self, db: StorageConnection) -> None:
        self._db = db

    def prune_expired(self, days_to_keep: int) -> None:
        cutoff = datetime.now(UTC) - timedelta(days=days_to_keep)
        with self._db.transaction():
            self._db.connection.execute(
                "DELETE FROM articles WHERE created_at < ?",
                (cutoff.isoformat(),),
            )
            self._db.connection.execute(
                "DELETE FROM jobs WHERE article_id NOT IN (SELECT article_id FROM articles)"
                " AND status != 'failed'"
            )

    def delete_incomplete_articles(self) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                DELETE FROM articles
                WHERE translation_status != 'done' OR summary_status != 'done'
                """
            )
            self._db.connection.execute(
                "DELETE FROM jobs WHERE article_id NOT IN (SELECT article_id FROM articles)"
                " AND status != 'failed'"
            )

    def has_article(self, article_id: str) -> bool:
        with self._db._lock:
            row = self._db.connection.execute(
                "SELECT 1 FROM known_article_ids WHERE article_id = ?",
                (article_id,),
            ).fetchone()
        return row is not None

    def upsert_article_source(self, article: ArticleContent) -> None:
        now = datetime.now(UTC).isoformat()
        with self._db.transaction():
            self._db.connection.execute(
                """
                INSERT INTO articles (
                    article_id, provider_id, provider_article_id, url, category, title, translated_title, author, published_at,
                    source_body, translated_body, summary, more_info, assigned_categories_json, translation_status,
                    summary_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, NULL, NULL, NULL, '[]', 'pending', 'pending', ?, ?)
                ON CONFLICT(article_id) DO UPDATE SET
                    provider_id = excluded.provider_id,
                    provider_article_id = excluded.provider_article_id,
                    url = excluded.url,
                    category = excluded.category,
                    title = excluded.title,
                    author = excluded.author,
                    published_at = excluded.published_at,
                    source_body = excluded.source_body,
                    updated_at = excluded.updated_at
                """,
                (
                    article.article_id,
                    article.provider_id,
                    article.provider_article_id,
                    article.url,
                    article.category,
                    article.title,
                    article.author,
                    article.published_at.isoformat() if article.published_at else None,
                    article.body,
                    now,
                    now,
                ),
            )

    def update_translation(
        self, article_id: str, translated_title: str | None, translated_body: str, status: str
    ) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                UPDATE articles
                SET translated_title = ?, translated_body = ?, translation_status = ?, updated_at = ?
                WHERE article_id = ?
                """,
                (translated_title, translated_body, status, datetime.now(UTC).isoformat(), article_id),
            )

    def complete_translation(
        self, article_id: str, translated_title: str | None, translated_body: str
    ) -> None:
        self._set_stage_result(
            article_id, "translation", "done",
            {"translated_title": translated_title, "translated_body": translated_body},
        )

    def fail_translation(self, article_id: str, error_text: str) -> None:
        self._set_stage_result(
            article_id, "translation", "failed",
            {"translated_title": None, "translated_body": ""},
            error_text=error_text, increment_attempt=True,
        )

    def reset_translation(self, article_id: str) -> None:
        self._set_stage_result(
            article_id, "translation", "pending",
            {"translated_title": None, "translated_body": None},
        )

    def update_summary(self, article_id: str, summary: str, status: str) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                UPDATE articles
                SET summary = ?, summary_status = ?, updated_at = ?
                WHERE article_id = ?
                """,
                (summary, status, datetime.now(UTC).isoformat(), article_id),
            )

    def replace_categories(self, article_id: str, categories: tuple[str, ...] | list[str]) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                UPDATE articles
                SET assigned_categories_json = ?, updated_at = ?
                WHERE article_id = ?
                """,
                (
                    _serialize_categories(categories),
                    datetime.now(UTC).isoformat(),
                    article_id,
                ),
            )

    def update_more_info(self, article_id: str, more_info: str) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                UPDATE articles
                SET more_info = ?, updated_at = ?
                WHERE article_id = ?
                """,
                (more_info, datetime.now(UTC).isoformat(), article_id),
            )

    def complete_summary(self, article_id: str, summary: str) -> None:
        self._set_stage_result(
            article_id, "summary", "done", {"summary": summary}, mark_known=True,
        )

    def fail_summary(self, article_id: str, error_text: str) -> None:
        self._set_stage_result(
            article_id, "summary", "failed", {"summary": ""},
            error_text=error_text, increment_attempt=True,
        )

    def reset_summary(self, article_id: str) -> None:
        self._set_stage_result(
            article_id, "summary", "pending", {"summary": None},
        )

    def _set_stage_result(
        self,
        article_id: str,
        job_type: str,
        status: str,
        article_updates: dict[str, str | None],
        error_text: str | None = None,
        increment_attempt: bool = False,
        mark_known: bool = False,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        status_column = f"{job_type}_status"
        article_updates[status_column] = status
        set_clause = ", ".join(f"{col} = ?" for col in article_updates)
        values = list(article_updates.values()) + [now, article_id]
        attempt_count = 1 if increment_attempt else 0
        with self._db.transaction():
            self._db.connection.execute(
                f"UPDATE articles SET {set_clause}, updated_at = ? WHERE article_id = ?",
                values,
            )
            self._db.connection.execute(
                """
                INSERT INTO jobs (article_id, job_type, status, error_text, attempt_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id, job_type) DO UPDATE SET
                    status = excluded.status,
                    error_text = excluded.error_text,
                    attempt_count = jobs.attempt_count + excluded.attempt_count,
                    updated_at = excluded.updated_at
                """,
                (article_id, job_type, status, error_text, attempt_count, now),
            )
            if mark_known:
                self._insert_known_article_id(article_id, now)

    def set_job_status(
        self,
        article_id: str,
        job_type: str,
        status: str,
        error_text: str | None = None,
        increment_attempt: bool = False,
        mark_known: bool = False,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._db.transaction():
            self._db.connection.execute(
                """
                INSERT INTO jobs (article_id, job_type, status, error_text, attempt_count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id, job_type) DO UPDATE SET
                    status = excluded.status,
                    error_text = excluded.error_text,
                    attempt_count = jobs.attempt_count + excluded.attempt_count,
                    updated_at = excluded.updated_at
                """,
                (article_id, job_type, status, error_text, 1 if increment_attempt else 0, now),
            )
            if mark_known:
                self._insert_known_article_id(article_id, now)

    def list_articles(self) -> list[ArticleRecord]:
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT article_id, provider_id, provider_article_id, url, category, title, translated_title, author,
                       published_at, source_body, translated_body, summary, more_info, translation_status,
                       summary_status, created_at, assigned_categories_json
                FROM articles
                ORDER BY rowid ASC
                """
            ).fetchall()
        return [self._article_from_row(row) for row in rows]

    def get_article(self, article_id: str) -> ArticleRecord | None:
        with self._db._lock:
            row = self._db.connection.execute(
                """
                SELECT article_id, provider_id, provider_article_id, url, category, title, translated_title, author,
                       published_at, source_body, translated_body, summary, more_info, translation_status,
                       summary_status, created_at, assigned_categories_json
                FROM articles
                WHERE article_id = ?
                """,
                (article_id,),
            ).fetchone()
        if row is None:
            return None
        return self._article_from_row(row)

    def _insert_known_article_id(self, article_id: str, first_seen_at: str) -> None:
        self._db.connection.execute(
            """
            INSERT INTO known_article_ids (article_id, first_seen_at)
            VALUES (?, ?)
            ON CONFLICT(article_id) DO NOTHING
            """,
            (article_id, first_seen_at),
        )

    @staticmethod
    def _article_from_row(row: sqlite3.Row) -> ArticleRecord:
        published_at = row["published_at"]
        created_at = row["created_at"]
        return ArticleRecord(
            article_id=row["article_id"],
            provider_id=row["provider_id"],
            provider_article_id=row["provider_article_id"],
            url=row["url"],
            category=row["category"],
            title=row["title"],
            translated_title=row["translated_title"],
            author=row["author"],
            published_at=datetime.fromisoformat(published_at) if published_at else None,
            source_body=row["source_body"],
            translated_body=row["translated_body"],
            summary=row["summary"],
            more_info=row["more_info"],
            translation_status=row["translation_status"],
            summary_status=row["summary_status"],
            created_at=datetime.fromisoformat(created_at),
            categories=_deserialize_categories(row["assigned_categories_json"]),
        )


def _serialize_categories(categories: tuple[str, ...] | list[str]) -> str:
    return json.dumps(list(normalize_article_categories(categories)))


def _deserialize_categories(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    try:
        raw = json.loads(value)
    except json.JSONDecodeError:
        return ()
    if not isinstance(raw, list):
        return ()
    return normalize_article_categories(item for item in raw if isinstance(item, str))
