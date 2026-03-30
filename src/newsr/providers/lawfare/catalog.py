from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("cybersecurity-tech", "Cybersecurity & Tech", "/topics/cybersecurity-tech"),
    TargetOption("surveillance-privacy", "Surveillance & Privacy", "/topics/surveillance-privacy"),
    TargetOption("intelligence", "Intelligence", "/topics/intelligence"),
    TargetOption(
        "foreign-relations-international-law",
        "Foreign Relations & International Law",
        "/topics/foreign-relations-international-law",
    ),
]
