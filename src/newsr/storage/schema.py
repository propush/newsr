from __future__ import annotations

from .connection import StorageConnection


def initialize_schema(db: StorageConnection) -> None:
    with db.transaction():
        db.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS providers (
                provider_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                settings_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS provider_targets (
                provider_id TEXT NOT NULL,
                target_key TEXT NOT NULL,
                target_kind TEXT NOT NULL,
                label TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                discovered_at TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (provider_id, target_key),
                FOREIGN KEY (provider_id) REFERENCES providers(provider_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS provider_target_selections (
                provider_id TEXT NOT NULL,
                target_key TEXT NOT NULL,
                selected INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (provider_id, target_key),
                FOREIGN KEY (provider_id, target_key) REFERENCES provider_targets(provider_id, target_key)
                    ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS articles (
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
            );
            CREATE TABLE IF NOT EXISTS jobs (
                article_id TEXT NOT NULL,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                error_text TEXT,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (article_id, job_type)
            );
            CREATE TABLE IF NOT EXISTS reader_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                article_id TEXT,
                view_mode TEXT NOT NULL,
                scroll_offset INTEGER NOT NULL,
                theme_name TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
