from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("latest", "Latest", "/"),
    TargetOption("higher-ed", "Higher Education", "/coverage-areas/higher-education"),
    TargetOption(
        "artificial-intelligence",
        "Artificial Intelligence",
        "/coverage-areas/artificial-intelligence",
    ),
    TargetOption("career-readiness", "Career Readiness", "/coverage-areas/career-readiness"),
    TargetOption("access-and-inclusion", "Access and Inclusion", "/coverage-areas/access-and-inclusion"),
    TargetOption("early-learning", "Early Learning", "/coverage-areas/early-learning"),
    TargetOption("education-workforce", "Education Workforce", "/coverage-areas/education-workforce"),
    TargetOption(
        "teaching-and-learning",
        "Teaching and Learning",
        "/coverage-areas/teaching-and-learning",
    ),
    TargetOption(
        "policy-and-government",
        "Policy and Government",
        "/coverage-areas/policy-and-government",
    ),
    TargetOption("edtech-business", "Edtech Business", "/coverage-areas/edtech-business"),
    TargetOption("assessments", "Assessments", "/coverage-areas/assessments"),
    TargetOption("digital-skills", "Digital Skills", "/coverage-areas/digital-skills"),
    TargetOption("media-literacy", "Media Literacy", "/coverage-areas/media-literacy"),
    TargetOption(
        "social-emotional-learning",
        "Social-Emotional Learning",
        "/coverage-areas/social-emotional-learning",
    ),
    TargetOption("digital-access", "Digital Access", "/coverage-areas/digital-access"),
    TargetOption("instructional-trends", "Instructional Trends", "/coverage-areas/instructional-trends"),
    TargetOption("data-privacy", "Data Privacy", "/coverage-areas/data-privacy"),
]
