from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("health_medicine", "Health & Medicine", "/news/health_medicine/"),
    TargetOption("computers_math", "Computers & Math", "/news/computers_math/"),
    TargetOption("earth_climate", "Earth & Climate", "/news/earth_climate/"),
    TargetOption("mind_brain", "Mind & Brain", "/news/mind_brain/"),
    TargetOption("matter_energy", "Matter & Energy", "/news/matter_energy/"),
    TargetOption("living_well", "Living Well", "/news/living_well/"),
    TargetOption("space_time", "Space & Time", "/news/space_time/"),
    TargetOption("plants_animals", "Plants & Animals", "/news/plants_animals/"),
    TargetOption("fossils_ruins", "Fossils & Ruins", "/news/fossils_ruins/"),
    TargetOption("science_society", "Science & Society", "/news/science_society/"),
    TargetOption("business_industry", "Business & Industry", "/news/business_industry/"),
    TargetOption("education_learning", "Education & Learning", "/news/education_learning/"),
    TargetOption("strange_offbeat", "Top News", "/news/strange_offbeat/"),
]
