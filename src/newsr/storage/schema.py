from __future__ import annotations

from datetime import UTC, datetime

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
            """
        )
        _initialize_article_schema(db)
        legacy_theme_name = _migrate_reader_state_schema(db)
        _initialize_options_schema(db, legacy_theme_name)


def _initialize_article_schema(db: StorageConnection) -> None:
    db.ensure_column(
        "articles",
        "assigned_categories_json",
        """TEXT NOT NULL DEFAULT '[]'""",
    )


def _migrate_reader_state_schema(db: StorageConnection) -> str | None:
    tables = {
        row["name"]
        for row in db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    if "reader_state" not in tables:
        _create_reader_state_table(db)
        return None

    columns = {
        row["name"]
        for row in db.connection.execute("PRAGMA table_info(reader_state)").fetchall()
    }
    if "scope_id" in columns:
        return None

    legacy_row = db.connection.execute(
        """
        SELECT article_id, view_mode, scroll_offset, theme_name, updated_at
        FROM reader_state
        WHERE id = 1
        """
    ).fetchone()
    db.connection.execute(
        """
        CREATE TABLE reader_state_new (
            scope_id TEXT PRIMARY KEY,
            article_id TEXT,
            view_mode TEXT NOT NULL,
            scroll_offset INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    legacy_theme_name = None
    if legacy_row is not None:
        legacy_theme_name = legacy_row["theme_name"]
        db.connection.execute(
            """
            INSERT INTO reader_state_new (scope_id, article_id, view_mode, scroll_offset, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "[ALL]",
                legacy_row["article_id"],
                legacy_row["view_mode"],
                legacy_row["scroll_offset"],
                legacy_row["updated_at"],
            ),
        )
    db.connection.execute("DROP TABLE reader_state")
    db.connection.execute("ALTER TABLE reader_state_new RENAME TO reader_state")
    return legacy_theme_name


def _create_reader_state_table(db: StorageConnection) -> None:
    db.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS reader_state (
            scope_id TEXT PRIMARY KEY,
            article_id TEXT,
            view_mode TEXT NOT NULL,
            scroll_offset INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def _initialize_options_schema(db: StorageConnection, legacy_theme_name: str | None) -> None:
    db.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            theme_name TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    if legacy_theme_name is None:
        return
    existing = db.connection.execute(
        "SELECT theme_name FROM options WHERE id = 1"
    ).fetchone()
    if existing is not None:
        return
    db.connection.execute(
        """
        INSERT INTO options (id, theme_name, updated_at)
        VALUES (1, ?, ?)
        """,
        (
            legacy_theme_name,
            datetime.now(UTC).isoformat(),
        ),
    )
