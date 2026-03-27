from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CategoryOption:
    slug: str
    label: str


BASE_CATEGORY_OPTIONS: tuple[CategoryOption, ...] = (
    CategoryOption("world", "World"),
    CategoryOption("technology", "Technology"),
    CategoryOption("business", "Business"),
    CategoryOption("entertainment_and_arts", "Entertainment And Arts"),
    CategoryOption("bbcindepth", "BBC InDepth"),
    CategoryOption("science-environment", "Science Environment"),
    CategoryOption("health", "Health"),
    CategoryOption("newsbeat", "Newsbeat"),
)


def merge_category_catalogs(
    base_categories: list[CategoryOption] | tuple[CategoryOption, ...],
    discovered_categories: list[CategoryOption],
) -> list[CategoryOption]:
    merged = list(base_categories)
    seen = {option.slug for option in base_categories}
    for option in discovered_categories:
        if option.slug in seen:
            continue
        merged.append(option)
        seen.add(option.slug)
    return merged
