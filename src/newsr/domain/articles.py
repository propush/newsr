from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ArticleRecord:
    article_id: str
    url: str
    category: str
    title: str
    translated_title: str | None
    author: str | None
    published_at: datetime | None
    source_body: str
    translated_body: str | None
    summary: str | None
    more_info: str | None
    translation_status: str
    summary_status: str
    created_at: datetime
    provider_id: str = ""
    provider_article_id: str = ""
    categories: tuple[str, ...] = ()


@dataclass(slots=True)
class SectionCandidate:
    article_id: str
    url: str
    category: str
    provider_id: str = ""
    provider_article_id: str = ""


@dataclass(slots=True)
class ArticleContent:
    article_id: str
    url: str
    category: str
    title: str
    author: str | None
    published_at: datetime | None
    body: str
    provider_id: str = ""
    provider_article_id: str = ""
