from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import UTC, datetime

from ..domain import ProviderRecord, ProviderTarget
from ..scheduling import is_due_on_schedule
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
                    INSERT INTO providers (
                        provider_id,
                        display_name,
                        enabled,
                        provider_type,
                        update_schedule,
                        settings_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider_id) DO UPDATE SET
                        display_name = excluded.display_name,
                        provider_type = excluded.provider_type,
                        settings_json = excluded.settings_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        provider.provider_id,
                        provider.display_name,
                        1 if provider.enabled else 0,
                        provider.provider_type,
                        provider.update_schedule,
                        json.dumps(provider.settings, sort_keys=True),
                        now,
                        now,
                    ),
                )

    def list_providers(self) -> list[ProviderRecord]:
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT provider_id, display_name, enabled, provider_type, update_schedule,
                       last_refresh_started_at, last_refresh_completed_at, settings_json
                FROM providers
                ORDER BY display_name ASC
                """
            ).fetchall()
        return [self._provider_from_row(row) for row in rows]

    def list_enabled_providers(self) -> list[ProviderRecord]:
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT provider_id, display_name, enabled, provider_type, update_schedule,
                       last_refresh_started_at, last_refresh_completed_at, settings_json
                FROM providers
                WHERE enabled = 1
                ORDER BY display_name ASC
                """
            ).fetchall()
        return [self._provider_from_row(row) for row in rows]

    def get_provider(self, provider_id: str) -> ProviderRecord | None:
        with self._db._lock:
            row = self._db.connection.execute(
                """
                SELECT provider_id, display_name, enabled, provider_type, update_schedule,
                       last_refresh_started_at, last_refresh_completed_at, settings_json
                FROM providers
                WHERE provider_id = ?
                """,
                (provider_id,),
            ).fetchone()
        if row is None:
            return None
        return self._provider_from_row(row)

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

    def update_provider_schedule(self, provider_id: str, update_schedule: str | None) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                """
                UPDATE providers
                SET update_schedule = ?, updated_at = ?
                WHERE provider_id = ?
                """,
                (update_schedule, datetime.now(UTC).isoformat(), provider_id),
            )

    def create_topic_provider(
        self,
        *,
        display_name: str,
        topic_query: str,
        update_schedule: str | None,
        enabled: bool = True,
    ) -> ProviderRecord:
        now = datetime.now(UTC).isoformat()
        existing_provider = self.find_topic_provider(topic_query)
        if existing_provider is not None:
            raise ValueError(existing_provider.display_name)
        provider_id = self._build_topic_provider_id(display_name)
        settings = {"topic_query": topic_query}
        record = ProviderRecord(
            provider_id=provider_id,
            display_name=display_name,
            enabled=enabled,
            provider_type="topic",
            update_schedule=update_schedule,
            settings=settings,
        )
        with self._db.transaction():
            self._db.connection.execute(
                """
                INSERT INTO providers (
                    provider_id,
                    display_name,
                    enabled,
                    provider_type,
                    update_schedule,
                    settings_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider_id,
                    display_name,
                    1 if enabled else 0,
                    "topic",
                    update_schedule,
                    json.dumps(settings, sort_keys=True),
                    now,
                    now,
                ),
            )
            self._db.connection.execute(
                """
                INSERT INTO provider_targets (
                    provider_id, target_key, target_kind, label, payload_json, discovered_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider_id,
                    "watch",
                    "topic",
                    display_name,
                    json.dumps({"query": topic_query}, sort_keys=True),
                    None,
                    now,
                ),
            )
            self._db.connection.execute(
                """
                INSERT INTO provider_target_selections (provider_id, target_key, selected, updated_at)
                VALUES (?, ?, 1, ?)
                """,
                (provider_id, "watch", now),
            )
        return record

    def delete_provider(self, provider_id: str) -> None:
        with self._db.transaction():
            self._db.connection.execute(
                "DELETE FROM providers WHERE provider_id = ?",
                (provider_id,),
            )

    def mark_refresh_started(self, provider_id: str, started_at: datetime | None = None) -> None:
        timestamp = (started_at or datetime.now(UTC)).astimezone(UTC).isoformat()
        with self._db.transaction():
            self._db.connection.execute(
                """
                UPDATE providers
                SET last_refresh_started_at = ?, updated_at = ?
                WHERE provider_id = ?
                """,
                (timestamp, timestamp, provider_id),
            )

    def mark_refresh_completed(self, provider_id: str, completed_at: datetime | None = None) -> None:
        timestamp = (completed_at or datetime.now(UTC)).astimezone(UTC).isoformat()
        with self._db.transaction():
            self._db.connection.execute(
                """
                UPDATE providers
                SET last_refresh_completed_at = ?, updated_at = ?
                WHERE provider_id = ?
                """,
                (timestamp, timestamp, provider_id),
            )

    def find_topic_provider(self, topic_query: str) -> ProviderRecord | None:
        normalized_query = _normalize_topic_identity(topic_query)
        if not normalized_query:
            return None
        with self._db._lock:
            rows = self._db.connection.execute(
                """
                SELECT provider_id, display_name, enabled, provider_type, update_schedule,
                       last_refresh_started_at, last_refresh_completed_at, settings_json
                FROM providers
                WHERE provider_type = 'topic'
                ORDER BY created_at ASC
                """
            ).fetchall()
        for row in rows:
            provider = self._provider_from_row(row)
            existing_query = provider.settings.get("topic_query", provider.display_name)
            if _normalize_topic_identity(existing_query) == normalized_query:
                return provider
        return None

    def list_due_providers(self, default_schedule: str) -> list[ProviderRecord]:
        candidates = [
            provider
            for provider in self.list_enabled_providers()
            if provider.provider_type != "all"
        ]
        return [
            provider
            for provider in candidates
            if is_due_on_schedule(
                provider.update_schedule or default_schedule,
                last_completed_at=provider.last_refresh_completed_at,
            )
        ]

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
        last_refresh_started_at = row["last_refresh_started_at"]
        last_refresh_completed_at = row["last_refresh_completed_at"]
        return ProviderRecord(
            provider_id=row["provider_id"],
            display_name=row["display_name"],
            enabled=bool(row["enabled"]),
            provider_type=row["provider_type"],
            update_schedule=row["update_schedule"],
            last_refresh_started_at=(
                datetime.fromisoformat(last_refresh_started_at) if last_refresh_started_at else None
            ),
            last_refresh_completed_at=(
                datetime.fromisoformat(last_refresh_completed_at) if last_refresh_completed_at else None
            ),
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

    def _build_topic_provider_id(self, display_name: str) -> str:
        base_slug = _slugify(display_name) or "topic"
        base_provider_id = f"topic:{base_slug}"
        existing_ids = {
            row["provider_id"]
            for row in self._db.connection.execute(
                "SELECT provider_id FROM providers WHERE provider_id LIKE 'topic:%'"
            ).fetchall()
        }
        if base_provider_id not in existing_ids:
            return base_provider_id
        suffix = 2
        while f"{base_provider_id}-{suffix}" in existing_ids:
            suffix += 1
        return f"{base_provider_id}-{suffix}"


def _slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
    return collapsed


def _normalize_topic_identity(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value).strip()
    return collapsed.casefold()
