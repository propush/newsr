from __future__ import annotations

from datetime import UTC, datetime

from ..domain.reader import ReaderState, ViewMode
from .connection import StorageConnection


class ReaderStateStore:
    def __init__(self, db: StorageConnection) -> None:
        self._db = db

    def load(self, scope_id: str) -> ReaderState:
        with self._db._lock:
            row = self._db.connection.execute(
                """
                SELECT article_id, view_mode, scroll_offset
                FROM reader_state
                WHERE scope_id = ?
                """,
                (scope_id,),
            ).fetchone()
        if row is None:
            return ReaderState(article_id=None, view_mode=ViewMode.FULL, scroll_offset=0)
        return ReaderState(
            article_id=row["article_id"],
            view_mode=ViewMode(row["view_mode"]),
            scroll_offset=row["scroll_offset"],
        )

    def save(self, scope_id: str, state: ReaderState) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                INSERT INTO reader_state (scope_id, article_id, view_mode, scroll_offset, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(scope_id) DO UPDATE SET
                    article_id = excluded.article_id,
                    view_mode = excluded.view_mode,
                    scroll_offset = excluded.scroll_offset,
                    updated_at = excluded.updated_at
                """,
                (
                    scope_id,
                    state.article_id,
                    state.view_mode.value,
                    state.scroll_offset,
                    datetime.now(UTC).isoformat(),
                ),
            )
