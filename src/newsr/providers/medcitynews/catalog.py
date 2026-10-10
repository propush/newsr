from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = (
    TargetOption("health-tech", "Health Tech", "/category/channel/health-tech/"),
    TargetOption("biopharma", "BioPharma", "/category/channel/biopharma/"),
    TargetOption(
        "medical-devices-and-diagnostics",
        "Devices & Diagnostics",
        "/category/channel/medical-devices-and-diagnostics/",
    ),
    TargetOption("consumer-employer", "Consumer / Employer", "/category/channel/consumer-employer/"),
    TargetOption("news", "News", "/category/news/"),
    TargetOption("contributors", "Contributors", "/category/medcity-influencers/"),
    TargetOption(
        "artificial-intelligence",
        "Artificial Intelligence",
        "/category/channel/artificial-intelligence/",
    ),
    TargetOption("startups", "Startups", "/category/channel/startup-channel/"),
    TargetOption("payers", "Payers", "/category/channel/payers/"),
    TargetOption("providers", "Providers", "/category/channel/providers/"),
    TargetOption("policy", "Policy", "/category/channel/politics-channel/"),
)
