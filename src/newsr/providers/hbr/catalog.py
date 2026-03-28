from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("leadership", "Leadership", "/topic/subject/leadership"),
    TargetOption("strategy", "Strategy", "/topic/subject/strategy"),
    TargetOption("innovation", "Innovation", "/topic/subject/innovation"),
    TargetOption("managing-people", "Managing People", "/topic/subject/managing-people"),
    TargetOption("managing-yourself", "Managing Yourself", "/topic/subject/managing-yourself"),
]
