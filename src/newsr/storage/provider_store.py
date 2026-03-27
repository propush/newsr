from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from ..domain import ProviderRecord, ProviderTarget
from .connection import StorageConnection


class ProviderStore:
    def __init__(self, db: StorageConnection) -> None:
        self._db = db

    def sync_providers(self, providers: list[ProviderRecord]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._db.transaction():
            for provider in providers:
                self._db.connection.execute(
                    """
                    INSERT INTO providers (provider_id, display_name, enabled, settings_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider_id) DO UPDATE SET
                        display_name = excluded.display_name,
                        settings_json = excluded.settings_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        provider.provider_id,
                        provider.display_name,
                        1 if provider.enabled else 0,
                        json.dumps(provider.settings, sort_keys=True),
                        now,
                        now,
                    ),
                )

    def list_providers(self) -> list[ProviderRecord]:
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT provider_id, display_name, enabled, settings_json
                FROM providers
                ORDER BY display_name ASC
                """
            ).fetchall()
        return [self._provider_from_row(row) for row in rows]

    def list_enabled_providers(self) -> list[ProviderRecord]:
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT provider_id, display_name, enabled, settings_json
                FROM providers
                WHERE enabled = 1
                ORDER BY display_name ASC
                """
            ).fetchall()
        return [self._provider_from_row(row) for row in rows]

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                UPDATE providers
                SET enabled = ?, updated_at = ?
                WHERE provider_id = ?
                """,
                (1 if enabled else 0, datetime.now(UTC).isoformat(), provider_id),
            )

    def replace_provider_targets(self, provider_id: str, targets: list[ProviderTarget]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._db.transaction():
            self._db.connection.execute(
                "DELETE FROM provider_targets WHERE provider_id = ?",
                (provider_id,),
            )
            for target in targets:
                self._db.connection.execute(
                    """
                    INSERT INTO provider_targets (
                        provider_id, target_key, target_kind, label, payload_json, discovered_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        provider_id,
                        target.target_key,
                        target.target_kind,
                        target.label,
                        json.dumps(target.payload, sort_keys=True),
                        target.discovered_at.isoformat() if target.discovered_at else None,
                        now,
                    ),
                )
            if not targets:
                self._db.connection.execute(
                    "DELETE FROM provider_target_selections WHERE provider_id = ?",
                    (provider_id,),
                )
                return
            placeholders = ", ".join("?" for _ in targets)
            self._db.connection.execute(
                f"""
                DELETE FROM provider_target_selections
                WHERE provider_id = ? AND target_key NOT IN ({placeholders})
                """,
                (provider_id, *(target.target_key for target in targets)),
            )

    def list_provider_targets(self, provider_id: str) -> list[ProviderTarget]:
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT targets.provider_id, targets.target_key, targets.target_kind, targets.label,
                       targets.payload_json, targets.discovered_at, COALESCE(selections.selected, 0) AS selected
                FROM provider_targets AS targets
                LEFT JOIN provider_target_selections AS selections
                  ON selections.provider_id = targets.provider_id
                 AND selections.target_key = targets.target_key
                WHERE targets.provider_id = ?
                ORDER BY targets.rowid ASC
                """,
                (provider_id,),
            ).fetchall()
        return [self._target_from_row(row) for row in rows]

    def list_selected_targets(self, provider_id: str) -> list[ProviderTarget]:
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT targets.provider_id, targets.target_key, targets.target_kind, targets.label,
                       targets.payload_json, targets.discovered_at, 1 AS selected
                FROM provider_targets AS targets
                INNER JOIN provider_target_selections AS selections
                  ON selections.provider_id = targets.provider_id
                 AND selections.target_key = targets.target_key
                WHERE targets.provider_id = ? AND selections.selected = 1
                ORDER BY targets.rowid ASC
                """,
                (provider_id,),
            ).fetchall()
        return [self._target_from_row(row) for row in rows]

    def set_selected_targets(self, provider_id: str, target_keys: list[str]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._db.transaction():
            self._db.connection.execute(
                "DELETE FROM provider_target_selections WHERE provider_id = ?",
                (provider_id,),
            )
            for target_key in target_keys:
                self._db.connection.execute(
                    """
                    INSERT INTO provider_target_selections (provider_id, target_key, selected, updated_at)
                    VALUES (?, ?, 1, ?)
                    """,
                    (provider_id, target_key, now),
                )

    @staticmethod
    def _provider_from_row(row: sqlite3.Row) -> ProviderRecord:
        settings = json.loads(row["settings_json"]) if row["settings_json"] else {}
        return ProviderRecord(
            provider_id=row["provider_id"],
            display_name=row["display_name"],
            enabled=bool(row["enabled"]),
            settings=settings,
        )

    @staticmethod
    def _target_from_row(row: sqlite3.Row) -> ProviderTarget:
        discovered_at = row["discovered_at"]
        return ProviderTarget(
            provider_id=row["provider_id"],
            target_key=row["target_key"],
            target_kind=row["target_kind"],
            label=row["label"],
            payload=json.loads(row["payload_json"]) if row["payload_json"] else {},
            discovered_at=datetime.fromisoformat(discovered_at) if discovered_at else None,
            selected=bool(row["selected"]),
        )
