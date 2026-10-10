from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CategoryOption:
    slug: str
    label: str
    path: str | None = None


BASE_CATEGORY_OPTIONS: tuple[CategoryOption, ...] = (
    CategoryOption("world", "World"),
    CategoryOption("technology", "Technology", "/technology"),
    CategoryOption("business", "Business", "/business"),
    CategoryOption("entertainment_and_arts", "Entertainment & Arts", "/culture/entertainment-news"),
    CategoryOption("bbcindepth", "BBC InDepth"),
    CategoryOption("science-environment", "Science & Environment", "/news/science_and_environment"),
    CategoryOption("health", "Health", "/health"),
    CategoryOption("newsbeat", "Newsbeat"),
    CategoryOption("latest", "Latest", "/news"),
    CategoryOption("us-canada", "US & Canada"),
    CategoryOption("uk", "UK"),
    CategoryOption("world/africa", "Africa"),
    CategoryOption("world/asia", "Asia"),
    CategoryOption("world/australia", "Australia"),
    CategoryOption("world/europe", "Europe"),
    CategoryOption("world/latin_america", "Latin America"),
    CategoryOption("world/middle_east", "Middle East"),
    CategoryOption("bbcverify", "BBC Verify"),
    CategoryOption("politics", "UK Politics"),
    CategoryOption("england", "England"),
    CategoryOption("northern_ireland", "Northern Ireland"),
    CategoryOption("scotland", "Scotland"),
    CategoryOption("wales", "Wales"),
    CategoryOption("culture", "Culture", "/culture"),
    CategoryOption("arts", "Arts", "/arts"),
    CategoryOption("travel", "Travel", "/travel"),
    CategoryOption("earth", "Earth", "/future-planet"),
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
