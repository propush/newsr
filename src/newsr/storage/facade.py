from __future__ import annotations

from pathlib import Path
from typing import Any

from ..domain.reader import ReaderState
from .article_store import ArticleStore
from .connection import StorageConnection
from .provider_store import ProviderStore
from .reader_state_store import ReaderStateStore
from .schema import initialize_schema


class NewsStorage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._db = StorageConnection(path)
        self.connection = self._db.connection
        self._articles = ArticleStore(self._db)
        self._providers = ProviderStore(self._db)
        self._reader_state = ReaderStateStore(self._db)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._articles, name)

    def initialize(self) -> None:
        initialize_schema(self._db)

    def load_reader_state(self) -> ReaderState:
        return self._reader_state.load()

    def save_reader_state(self, state: ReaderState) -> None:
        self._reader_state.save(state)

    def sync_providers(self, providers) -> None:
        self._providers.sync_providers(providers)

    def list_providers(self):
        return self._providers.list_providers()

    def list_enabled_providers(self):
        return self._providers.list_enabled_providers()

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> None:
        self._providers.set_provider_enabled(provider_id, enabled)

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
