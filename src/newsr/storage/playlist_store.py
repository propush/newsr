from __future__ import annotations

from ..domain.playlist import PlaylistItem
from .connection import StorageConnection


class PlaylistStore:
    def __init__(self, db: StorageConnection) -> None:
        self._db = db

    def load(self) -> list[PlaylistItem]:
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT article_id, scope_id
                FROM playlist
                WHERE article_id IN (SELECT article_id FROM articles)
                ORDER BY position ASC
                """
            ).fetchall()
        return [PlaylistItem(article_id=row["article_id"], scope_id=row["scope_id"]) for row in rows]

    def save(self, items: list[PlaylistItem]) -> None:
        with self._db.transaction():
            self._db.connection.execute("DELETE FROM playlist")
            self._db.connection.executemany(
                "INSERT INTO playlist (position, article_id, scope_id) VALUES (?, ?, ?)",
                [(position, item.article_id, item.scope_id) for position, item in enumerate(items)],
            )
