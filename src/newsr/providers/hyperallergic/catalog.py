from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = (
    TargetOption("news", "News", "/tag/news/"),
    TargetOption("reviews", "Reviews", "/tag/reviews/"),
    TargetOption("opinion", "Opinion", "/tag/opinion/"),
    TargetOption("film", "Film", "/tag/film/"),
)
