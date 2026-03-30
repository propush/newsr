from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("grid-edge", "Grid Edge", "/articles/grid-edge"),
    TargetOption("energy-storage", "Energy Storage", "/articles/energy-storage"),
    TargetOption("solar", "Solar", "/articles/solar"),
    TargetOption("electrification", "Electrification", "/articles/electrification"),
    TargetOption("transportation", "Transportation", "/articles/transportation"),
]
