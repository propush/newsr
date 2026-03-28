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
    TargetOption(
        "consumer-employer",
        "Consumer / Employer",
        "/category/channel/consumer-employer/",
    ),
)
