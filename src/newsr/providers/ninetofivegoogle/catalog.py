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
    TargetOption("pixel-watch", "Pixel Watch", "/guides/google-pixel-watch/"),
    TargetOption("samsung", "Samsung", "/guides/samsung/"),
    TargetOption("oneplus", "OnePlus", "/guides/oneplus/"),
    TargetOption("oppo", "Oppo", "/guides/oppo/"),
    TargetOption("xiaomi", "Xiaomi", "/guides/xiaomi/"),
    TargetOption("android-tv", "Android TV", "/guides/android-tv/"),
    TargetOption("chromecast", "Chromecast", "/guides/chromecast/"),
    TargetOption("gmail", "Gmail", "/guides/gmail/"),
    TargetOption("google-meet", "Google Meet", "/guides/google-meet/"),
    TargetOption("google-chat", "Google Chat", "/guides/google-chat/"),
    TargetOption("google-calendar", "Google Calendar", "/guides/google-calendar/"),
    TargetOption("google-keep", "Google Keep", "/guides/google-keep/"),
    TargetOption("google-drive", "Google Drive", "/guides/google-drive/"),
    TargetOption("google-docs", "Google Docs", "/guides/google-docs/"),
]
