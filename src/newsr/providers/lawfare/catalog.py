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
    TargetOption("armed-conflict", "Armed Conflict", "/topics/armed-conflict"),
    TargetOption("congress", "Congress", "/topics/congress"),
    TargetOption("courts-litigation", "Courts & Litigation", "/topics/courts-litigation"),
    TargetOption(
        "criminal-justice-rule-of-law",
        "Criminal Justice & Rule of Law",
        "/topics/criminal-justice-rule-of-law",
    ),
    TargetOption("democracy-elections", "Democracy & Elections", "/topics/democracy-elections"),
    TargetOption("executive-branch", "Executive Branch", "/topics/executive-branch"),
    TargetOption("states-localities", "States & Localities", "/topics/states-localities"),
    TargetOption("terrorism-extremism", "Terrorism & Extremism", "/topics/terrorism-extremism"),
]
