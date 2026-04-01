from __future__ import annotations

from collections.abc import Iterable


ARTICLE_CATEGORIES: tuple[str, ...] = (
    "ADVERTISEMENT",
    "SPORT",
    "TECHNOLOGIES",
    "AI",
    "LIFE",
    "MEETUP",
    "BUSINESS",
    "POLITICS",
    "WAR",
    "SCIENCE",
    "HEALTH",
    "SECURITY",
    "CULTURE",
)

_ARTICLE_CATEGORY_SET = frozenset(ARTICLE_CATEGORIES)


def normalize_article_category(value: str) -> str | None:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    if normalized in _ARTICLE_CATEGORY_SET:
        return normalized
    return None


def normalize_article_categories(values: Iterable[str]) -> tuple[str, ...]:
    requested = {
        normalized
        for value in values
        if isinstance(value, str)
        for normalized in [normalize_article_category(value)]
        if normalized is not None
    }
    return tuple(category for category in ARTICLE_CATEGORIES if category in requested)
