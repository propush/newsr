from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("latest", "Latest", "/"),
    TargetOption("pixel", "Pixel", "/guides/pixel/"),
    TargetOption("android", "Android", "/guides/android/"),
    TargetOption("chrome", "Chrome", "/guides/chrome/"),
    TargetOption("tv", "TV", "/guides/tv/"),
    TargetOption("workspace", "Workspace", "/guides/workspace/"),
    TargetOption("assistant", "Assistant", "/guides/assistant/"),
    TargetOption("smart-home", "Smart Home", "/guides/smart-home/"),
    TargetOption("cars", "Cars", "/guides/cars/"),
    TargetOption("reviews", "Reviews", "/guides/review/"),
    TargetOption("how-to", "How Tos", "/guides/how-to/"),
    TargetOption("deals", "Deals", "/guides/deals/"),
]
