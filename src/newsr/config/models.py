from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ArticlesConfig:
    fetch: int
    store: int


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
class UILocaleConfig:
    locale: str


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
    ui: UILocaleConfig
    export: ExportConfig
