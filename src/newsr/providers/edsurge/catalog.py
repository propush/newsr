from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("k12", "K-12", "/news/k-12"),
    TargetOption("higher-ed", "Higher Ed", "/news/higher-ed"),
    TargetOption(
        "artificial-intelligence",
        "Artificial Intelligence",
        "/news/topics/artificial-intelligence",
    ),
]
