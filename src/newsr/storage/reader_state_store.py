from __future__ import annotations

from datetime import UTC, datetime

from ..domain.reader import ReaderState, ViewMode
from .connection import StorageConnection


class ReaderStateStore:
    def __init__(self, db: StorageConnection) -> None:
        self._db = db

    def load(self) -> ReaderState:
        with self._db._lock:
            row = self._db.connection.execute(
                "SELECT article_id, view_mode, scroll_offset, theme_name FROM reader_state WHERE id = 1"
            ).fetchone()
        if row is None:
            return ReaderState(article_id=None, view_mode=ViewMode.FULL, scroll_offset=0)
        return ReaderState(
            article_id=row["article_id"],
            view_mode=ViewMode(row["view_mode"]),
            scroll_offset=row["scroll_offset"],
            theme_name=row["theme_name"],
        )

    def save(self, state: ReaderState) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                INSERT INTO reader_state (id, article_id, view_mode, scroll_offset, theme_name, updated_at)
                VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    article_id = excluded.article_id,
                    view_mode = excluded.view_mode,
                    scroll_offset = excluded.scroll_offset,
                    theme_name = excluded.theme_name,
                    updated_at = excluded.updated_at
                """,
                (
                    state.article_id,
                    state.view_mode.value,
                    state.scroll_offset,
                    state.theme_name,
                    datetime.now(UTC).isoformat(),
                ),
            )
