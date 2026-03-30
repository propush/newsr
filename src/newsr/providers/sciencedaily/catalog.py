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
]
