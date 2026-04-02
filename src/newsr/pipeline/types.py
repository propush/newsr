from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


StatusCallback = Callable[[str], None]
ArticleReadyCallback = Callable[[str], None]


@dataclass(slots=True)
class RefreshResult:
    new_articles: int
    failed_articles: int
    processed_providers: int = 0


@dataclass(slots=True)
class RefreshProgress:
    completed_articles: int
    total_articles: int
