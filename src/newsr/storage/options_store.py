from __future__ import annotations

from datetime import UTC, datetime

from ..domain import AppOptions
from .connection import StorageConnection


class OptionsStore:
    def __init__(self, db: StorageConnection) -> None:
        self._db = db

    def load(self) -> AppOptions:
        with self._db._lock:
            row = self._db.connection.execute(
                "SELECT theme_name FROM options WHERE id = 1"
            ).fetchone()
        if row is None:
            return AppOptions()
        return AppOptions(theme_name=row["theme_name"])

    def save(self, options: AppOptions) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                INSERT INTO options (id, theme_name, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    theme_name = excluded.theme_name,
                    updated_at = excluded.updated_at
                """,
                (
                    options.theme_name,
                    datetime.now(UTC).isoformat(),
                ),
            )
