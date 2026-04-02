from __future__ import annotations

from pathlib import Path
from typing import Any

from ..domain import AppOptions
from ..domain.reader import ReaderState
from .article_store import ArticleStore
from .connection import StorageConnection
from .options_store import OptionsStore
from .provider_store import ProviderStore
from .reader_state_store import ReaderStateStore
from .schema import initialize_schema


class NewsStorage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._db = StorageConnection(path)
        self.connection = self._db.connection
        self._articles = ArticleStore(self._db)
        self._options = OptionsStore(self._db)
        self._providers = ProviderStore(self._db)
        self._reader_state = ReaderStateStore(self._db)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._articles, name)

    def initialize(self) -> None:
        initialize_schema(self._db)

    def load_options(self) -> AppOptions:
        return self._options.load()

    def save_options(self, options: AppOptions) -> None:
        self._options.save(options)

    def load_reader_state(self, scope_id: str) -> ReaderState:
        return self._reader_state.load(scope_id)

    def save_reader_state(self, scope_id: str, state: ReaderState) -> None:
        self._reader_state.save(scope_id, state)

    def sync_providers(self, providers) -> None:
        self._providers.sync_providers(providers)

    def list_providers(self):
        return self._providers.list_providers()

    def list_enabled_providers(self):
        return self._providers.list_enabled_providers()

    def get_provider(self, provider_id: str):
        return self._providers.get_provider(provider_id)

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> None:
        self._providers.set_provider_enabled(provider_id, enabled)

    def update_provider_schedule(self, provider_id: str, update_schedule: str | None) -> None:
        self._providers.update_provider_schedule(provider_id, update_schedule)

    def create_topic_provider(
        self,
        *,
        display_name: str,
        topic_query: str,
        update_schedule: str | None,
        enabled: bool = True,
    ):
        return self._providers.create_topic_provider(
            display_name=display_name,
            topic_query=topic_query,
            update_schedule=update_schedule,
            enabled=enabled,
        )

    def find_topic_provider(self, topic_query: str):
        return self._providers.find_topic_provider(topic_query)

    def delete_provider(self, provider_id: str) -> None:
        self._providers.delete_provider(provider_id)

    def mark_refresh_started(self, provider_id: str) -> None:
        self._providers.mark_refresh_started(provider_id)

    def mark_refresh_completed(self, provider_id: str) -> None:
        self._providers.mark_refresh_completed(provider_id)

    def list_due_providers(self, default_schedule: str):
        return self._providers.list_due_providers(default_schedule)

    def replace_provider_targets(self, provider_id: str, targets) -> None:
        self._providers.replace_provider_targets(provider_id, targets)

    def list_provider_targets(self, provider_id: str):
        return self._providers.list_provider_targets(provider_id)

    def list_selected_targets(self, provider_id: str):
        return self._providers.list_selected_targets(provider_id)

    def set_selected_targets(self, provider_id: str, target_keys: list[str]) -> None:
        self._providers.set_selected_targets(provider_id, target_keys)

    def close(self) -> None:
        self._db.close()
