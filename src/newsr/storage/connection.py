from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Iterator


class StorageConnection:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            try:
                yield
            except Exception:
                self.connection.rollback()
                raise
            else:
                self.connection.commit()

    def ensure_column(self, table_name: str, column_name: str, column_sql: str) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in columns:
            return
        self.connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
        )

    def close(self) -> None:
        with self._lock:
            self.connection.close()
