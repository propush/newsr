from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..scheduling import DEFAULT_UPDATE_SCHEDULE, validate_cron_expression
from ..ui_text import parse_ui_locale
from .models import (
    AppConfig,
    ArticlesConfig,
    ExportConfig,
    ExportImageConfig,
    LLMConfig,
    ProviderSortConfig,
    TranslationConfig,
    UIConfig,
)


def load_config(path: Path) -> AppConfig:
    raw = _load_raw_config(path)
    return AppConfig(
        articles=_load_articles(raw.get("articles", {})),
        llm=_load_llm(raw.get("llm", {})),
        translation=_load_translation(raw.get("translation", {})),
        ui=_load_ui(raw.get("ui", {})),
        export=_load_export(raw.get("export", {})),
    )


def _load_articles(raw: dict) -> ArticlesConfig:
    fetch = int(raw.get("fetch", 5))
    store = int(raw.get("store", 10))
    update_schedule = validate_cron_expression(str(raw.get("update_schedule", DEFAULT_UPDATE_SCHEDULE)))
    if fetch <= 0:
        raise ValueError("articles.fetch must be positive")
    if store <= 0:
        raise ValueError("articles.store must be positive")
    return ArticlesConfig(fetch=fetch, store=store, update_schedule=update_schedule)


def _load_llm(raw: dict) -> LLMConfig:
    url = str(raw.get("url", "")).rstrip("/")
    model_translation = str(raw.get("model_translation", "")).strip()
    model_summary = str(raw.get("model_summary", "")).strip()
    api_key = _load_optional_string(raw.get("api_key"))
    headers = _load_headers(raw.get("headers"))
    request_retries = int(raw.get("request_retries", 2))
    if not url:
        raise ValueError("llm.url is required")
    if not model_translation:
        raise ValueError("llm.model_translation is required")
    if not model_summary:
        raise ValueError("llm.model_summary is required")
    if request_retries < 0:
        raise ValueError("llm.request_retries must be non-negative")
    return LLMConfig(
        url=url,
        model_translation=model_translation,
        model_summary=model_summary,
        api_key=api_key,
        headers=headers,
        request_retries=request_retries,
    )


def _load_translation(raw: dict) -> TranslationConfig:
    target_language = str(raw.get("target_language", "")).strip()
    if not target_language:
        raise ValueError("translation.target_language is required")
    return TranslationConfig(target_language=target_language)


def _load_ui(raw: dict) -> UIConfig:
    locale = parse_ui_locale(raw.get("locale"))
    if locale is None:
        raise ValueError("ui.locale is required")
    return UIConfig(
        locale=locale,
        show_all=_load_bool(raw.get("show-all"), default=True, field_name="ui.show-all"),
        provider_sort=_load_provider_sort(raw.get("provider_sort", {})),
    )


def _load_provider_sort(raw: object) -> ProviderSortConfig:
    if not isinstance(raw, dict):
        raw = {}
    primary = str(raw.get("primary", "unread")).strip().lower()
    direction = str(raw.get("direction", "desc")).strip().lower()
    if primary not in {"name", "unread"}:
        raise ValueError("ui.provider_sort.primary must be one of: name, unread")
    if direction not in {"asc", "desc"}:
        raise ValueError("ui.provider_sort.direction must be one of: asc, desc")
    return ProviderSortConfig(primary=primary, direction=direction)


def _load_export(raw: dict) -> ExportConfig:
    image_raw = raw.get("image", {})
    if not isinstance(image_raw, dict):
        image_raw = {}
    quality = str(image_raw.get("quality", "hd")).strip().lower()
    if quality not in {"hd", "fhd"}:
        raise ValueError("export.image.quality must be one of: hd, fhd")
    return ExportConfig(image=ExportImageConfig(quality=quality))


def _load_raw_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("config root must be a mapping")
    return raw


def _load_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _load_headers(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("llm.headers must be a mapping")
    headers: dict[str, str] = {}
    for key, header_value in value.items():
        if key is None or header_value is None:
            raise ValueError("llm.headers keys and values must be non-empty strings")
        header_name = str(key).strip()
        header_text = str(header_value).strip()
        if not header_name or not header_text:
            raise ValueError("llm.headers keys and values must be non-empty strings")
        headers[header_name] = header_text
    return headers


def _load_bool(value: Any, *, default: bool, field_name: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be true or false")
