from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("pc-components", "PC Components", "/pc-components"),
    TargetOption("cpus", "CPUs", "/pc-components/cpus"),
    TargetOption("gpus", "GPUs", "/pc-components/gpus"),
    TargetOption("storage", "Storage", "/pc-components/storage"),
    TargetOption("laptops", "Laptops", "/laptops/news"),
    TargetOption("desktops", "Desktops", "/desktops"),
    TargetOption("software", "Software", "/software"),
    TargetOption(
        "artificial-intelligence",
        "Artificial Intelligence",
        "/tech-industry/artificial-intelligence",
    ),
]
