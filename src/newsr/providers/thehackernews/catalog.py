from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SectionOption:
    slug: str
    label: str
    path: str


BASE_SECTION_OPTIONS: tuple[SectionOption, ...] = (
    SectionOption(
        slug="threat-intelligence",
        label="Threat Intelligence",
        path="/search/label/Threat%20Intelligence",
    ),
    SectionOption(
        slug="cyber-attacks",
        label="Cyber Attacks",
        path="/search/label/Cyber%20Attack",
    ),
    SectionOption(
        slug="vulnerabilities",
        label="Vulnerabilities",
        path="/search/label/Vulnerable",
    ),
    SectionOption(
        slug="expert-insights",
        label="Expert Insights",
        path="/expert-insights/",
    ),
)
