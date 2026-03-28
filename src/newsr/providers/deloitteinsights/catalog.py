from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str
    search_tag: str


BASE_TARGET_OPTIONS = (
    TargetOption(
        "business-strategy-growth",
        "Strategy",
        "/us/en/insights/topics/business-strategy-growth.html",
        "Strategy",
    ),
    TargetOption(
        "technology-management",
        "Technology",
        "/us/en/insights/topics/technology-management.html",
        "Technology management",
    ),
    TargetOption(
        "talent",
        "Workforce",
        "/us/en/insights/topics/talent.html",
        "Talent",
    ),
    TargetOption(
        "operations",
        "Operations",
        "/us/en/insights/topics/operations.html",
        "Operations",
    ),
    TargetOption(
        "economy",
        "Economics",
        "/us/en/insights/topics/economy.html",
        "Economics",
    ),
)
