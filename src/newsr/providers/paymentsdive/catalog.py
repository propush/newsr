from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("latest", "Latest", "/"),
    TargetOption("retail", "Retail", "/topic/retail/"),
    TargetOption("banking", "Banking", "/topic/banking/"),
    TargetOption("restaurants", "Restaurants", "/topic/restaurants/"),
    TargetOption("regulations_and_policy", "Regulations & Policy", "/topic/regulations_and_policy/"),
    TargetOption("risk", "Consumer Risk", "/topic/risk/"),
    TargetOption("technology", "Technology", "/topic/technology/"),
    TargetOption("b2b", "B2B", "/topic/b2b/"),
    TargetOption("fraud", "Fraud", "/topic/fraud/"),
]
