from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = (
    TargetOption("news", "News", "/tag/news/"),
    TargetOption("reviews", "Reviews", "/tag/review/"),
    TargetOption("opinion", "Opinion", "/tag/opinion/"),
    TargetOption("film", "Film", "/tag/film/"),
    TargetOption("features", "Features", "/tag/feature/"),
    TargetOption("interviews", "Interviews", "/tag/interview/"),
    TargetOption("community", "Community", "/tag/community/"),
    TargetOption("guides", "Guides", "/tag/guide/"),
    TargetOption("opportunities", "Opportunities", "/tag/opportunities/"),
    TargetOption("announcements", "Announcements", "/tag/announcement/"),
    TargetOption("books", "Books", "/tag/books/"),
    TargetOption("comics", "Comics", "/tag/comics/"),
)
