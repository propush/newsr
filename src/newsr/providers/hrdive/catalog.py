from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("talent", "Talent", "/topic/talent/"),
    TargetOption("compensation-benefits", "Comp & Benefits", "/topic/compensation-benefits/"),
    TargetOption("diversity-inclusion", "Diversity & Inclusion", "/topic/diversity-inclusion/"),
    TargetOption("learning", "Learning", "/topic/learning/"),
    TargetOption("hr-management", "HR Management", "/topic/hr-management/"),
    TargetOption("compliance", "Compliance", "/topic/legal/"),
    TargetOption("hr-technology-analytics", "Tech & Analytics", "/topic/hr-technology-analytics/"),
    TargetOption("state-local-laws", "State & Local Laws", "/topic/state-local-laws/"),
]
