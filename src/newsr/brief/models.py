from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BriefPeriod(StrEnum):
    LAST_24H = "last_24h"
    LAST_WEEK = "last_week"
    ALL_UNREAD = "all_unread"


@dataclass(frozen=True, slots=True)
class BriefOptions:
    period: BriefPeriod = BriefPeriod.LAST_24H
    include_topics: bool = False
    mark_read: bool = True
    only_unread: bool = True


@dataclass(frozen=True, slots=True)
class BriefArticle:
    number: int
    article_id: str
    provider_id: str
    provider_name: str
    title: str
    summary: str
    published_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class BriefProgress:
    completed: int
    total: int
    message_key: str
    message_args: dict[str, object]


@dataclass(frozen=True, slots=True)
class BriefResult:
    report: str
    articles: list[BriefArticle]
    provider_ids: list[str]


@dataclass(frozen=True, slots=True)
class BriefBatch:
    text: str
    article_numbers: frozenset[int]
    articles: tuple[BriefArticle, ...] = ()


ProgressCallback = Callable[[BriefProgress], None]
Clock = Callable[[], datetime]
