from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("latest", "Latest", "/"),
    TargetOption("pixel", "Pixel", "/guides/google-pixel/"),
    TargetOption("android", "Android", "/guides/android/"),
    TargetOption("chrome", "Chrome", "/guides/google-chrome/"),
    TargetOption("tv", "TV", "/guides/google-tv/"),
    TargetOption("workspace", "Workspace", "/guides/google-workspace/"),
    TargetOption("assistant", "Assistant", "/guides/google-assistant/"),
    TargetOption("smart-home", "Smart Home", "/guides/smart-home/"),
    TargetOption("cars", "Cars", "/guides/cars/"),
    TargetOption("reviews", "Reviews", "/feature/review/"),
    TargetOption("how-to", "How Tos", "/guides/how-to/"),
    TargetOption("deals", "Deals", "/guides/deals/"),
    TargetOption("gemini", "Gemini", "/guides/gemini/"),
    TargetOption("nest", "Nest", "/guides/google-nest/"),
    TargetOption("chromeos", "ChromeOS", "/guides/chrome-os/"),
    TargetOption("android-auto", "Android Auto", "/guides/android-auto/"),
    TargetOption("wear-os", "Wear OS", "/guides/wear-os/"),
    TargetOption("youtube", "YouTube", "/guides/youtube/"),
    TargetOption("youtube-music", "YouTube Music", "/guides/youtube-music/"),
    TargetOption("youtube-tv", "YouTube TV", "/guides/youtube-tv/"),
    TargetOption("exclusives", "Exclusives", "/feature/exclusives/"),
]
