from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str
    kind: str


BASE_TARGET_OPTIONS = [
    TargetOption("latest", "Latest", "/", "feed"),
    TargetOption("gadgets", "Gadgets", "/gadgets/", "category"),
    TargetOption("science", "Science", "/science/", "category"),
    TargetOption("security", "Security", "/security/", "category"),
    TargetOption("tech-policy", "Tech Policy", "/tech-policy/", "category"),
    TargetOption("space", "Space", "/space/", "category"),
    TargetOption("ai", "AI", "/ai/", "category"),
    TargetOption("gaming", "Gaming", "/gaming/", "category"),
    TargetOption("cars", "Cars", "/cars/", "category"),
    TargetOption("information-technology", "Biz & IT", "/information-technology/", "category"),
    TargetOption("health", "Health", "/health/", "category"),
    TargetOption("culture", "Culture", "/culture/", "category"),
]
