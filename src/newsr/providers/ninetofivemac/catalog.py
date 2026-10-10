from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("latest", "Latest", "/"),
    TargetOption("iphone", "iPhone", "/guides/iphone/"),
    TargetOption("mac", "Mac", "/guides/mac/"),
    TargetOption("ipad", "iPad", "/guides/ipad/"),
    TargetOption("apple-watch", "Apple Watch", "/guides/apple-watch/"),
    TargetOption("vision-pro", "Vision Pro", "/guides/vision-pro/"),
    TargetOption("apple-tv", "Apple TV", "/guides/apple-tv/"),
    TargetOption("airpods", "AirPods", "/guides/airpods/"),
    TargetOption("homekit", "HomeKit", "/guides/homekit/"),
    TargetOption("reviews", "Reviews", "/guides/review/"),
    TargetOption("how-to", "How Tos", "/guides/how-to/"),
    TargetOption("app-store", "App Store", "/guides/app-store/"),
    TargetOption("apple-music", "Apple Music", "/guides/apple-music/"),
    TargetOption("carplay", "CarPlay", "/guides/carplay/"),
    TargetOption("siri", "Siri", "/guides/siri/"),
    TargetOption("apple-silicon", "Apple Silicon", "/guides/apple-silicon/"),
    TargetOption("apple-arcade", "Apple Arcade", "/guides/apple-arcade/"),
    TargetOption("aapl", "AAPL", "/guides/aapl/"),
    TargetOption("ios", "iOS", "/guides/ios/"),
    TargetOption("ipados", "iPadOS", "/guides/ipados/"),
    TargetOption("macos", "macOS", "/guides/macos/"),
    TargetOption("watchos", "watchOS", "/guides/watchos/"),
    TargetOption("visionos", "visionOS", "/guides/visionos/"),
    TargetOption("apple-health", "Apple Health", "/guides/apple-health/"),
    TargetOption("apple-store", "Apple Store", "/guides/apple-store/"),
    TargetOption("apple-card", "Apple Card", "/guides/apple-card/"),
    TargetOption("apple-one", "Apple One", "/guides/apple-one/"),
    TargetOption("apple-fitness", "Apple Fitness+", "/guides/apple-fitness/"),
    TargetOption("ai", "AI", "/guides/ai/"),
]
