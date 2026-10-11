from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from newsr.storage import NewsStorage


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
