from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("leadership", "Leadership", "/topic/subject/leadership"),
    TargetOption("strategy", "Strategy", "/topic/subject/strategy"),
    TargetOption("innovation", "Innovation", "/topic/subject/innovation"),
    TargetOption("managing-people", "Managing People", "/topic/subject/managing-people"),
    TargetOption("managing-yourself", "Managing Yourself", "/topic/subject/managing-yourself"),
    TargetOption("gender", "Gender", "/topic/subject/gender"),
    TargetOption("work-life-balance", "Work-life Balance", "/topic/subject/work-life-balance"),
    TargetOption(
        "technology-and-analytics",
        "Technology and Analytics",
        "/topic/subject/technology-and-analytics",
    ),
    TargetOption(
        "organizational-culture",
        "Organizational Culture",
        "/topic/subject/organizational-culture",
    ),
    TargetOption("marketing", "Marketing", "/topic/subject/marketing"),
    TargetOption(
        "business-communication",
        "Business Communication",
        "/topic/subject/business-communication",
    ),
    TargetOption("economics", "Economics", "/topic/subject/economics"),
    TargetOption(
        "decision-making-and-problem-solving",
        "Decision Making and Problem Solving",
        "/topic/subject/decision-making-and-problem-solving",
    ),
    TargetOption("competitive-strategy", "Competitive Strategy", "/topic/subject/competitive-strategy"),
    TargetOption("customer-experience", "Customer Experience", "/topic/subject/customer-experience"),
    TargetOption(
        "international-business",
        "International Business",
        "/topic/subject/international-business",
    ),
    TargetOption("career-planning", "Career Planning", "/topic/subject/career-planning"),
]
