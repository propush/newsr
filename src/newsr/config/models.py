from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ArticlesConfig:
    fetch: int
    store: int
    timeout: int
    update_schedule: str


@dataclass(slots=True)
class LLMConfig:
    url: str
    model_translation: str
    model_summary: str
    api_key: str | None = None
    headers: dict[str, str] | None = None
    request_retries: int = 2


@dataclass(slots=True)
class TranslationConfig:
    target_language: str


@dataclass(slots=True)
class ProviderSortConfig:
    primary: str
    direction: str


@dataclass(slots=True)
class UIConfig:
    locale: str
    show_all: bool
    provider_sort: ProviderSortConfig


@dataclass(slots=True)
class ExportImageConfig:
    quality: str


@dataclass(slots=True)
class ExportConfig:
    image: ExportImageConfig


@dataclass(slots=True)
class AppConfig:
    articles: ArticlesConfig
    llm: LLMConfig
    translation: TranslationConfig
    ui: UIConfig
    export: ExportConfig
