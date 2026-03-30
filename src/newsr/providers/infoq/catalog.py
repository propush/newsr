from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = (
    TargetOption("software-architecture", "Software Architecture", "/architecture/"),
    TargetOption("cloud-architecture", "Cloud Architecture", "/cloud-architecture/"),
    TargetOption("devops", "DevOps", "/devops/"),
    TargetOption("ai-ml-data-engineering", "AI, ML & Data Engineering", "/ai-ml-data-eng/"),
    TargetOption("java", "Java", "/java/"),
)
