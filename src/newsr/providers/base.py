from __future__ import annotations

from typing import Protocol

from ..cancellation import RefreshCancellation
from ..domain import ArticleContent, ProviderTarget, SectionCandidate


class NewsProvider(Protocol):
    provider_id: str
    display_name: str

    def default_targets(self) -> list[ProviderTarget]:
        ...

    def discover_targets(
        self, cancellation: RefreshCancellation | None = None
    ) -> list[ProviderTarget]:
        ...

    def fetch_candidates(
        self,
        target: ProviderTarget,
        limit: int,
        cancellation: RefreshCancellation | None = None,
    ) -> list[SectionCandidate]:
        ...

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        ...
