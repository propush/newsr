from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TargetOption:
    slug: str
    label: str
    path: str


BASE_TARGET_OPTIONS = [
    TargetOption("brand-strategy", "Brand Strategy", "/topic/brand-strategy/"),
    TargetOption("mobile", "Mobile", "/topic/mobile-marketing/"),
    TargetOption("creative", "Creative", "/topic/creative/"),
    TargetOption("social-media", "Social Media", "/topic/social-media/"),
    TargetOption("video", "Video", "/topic/video/"),
    TargetOption("agencies", "Agencies", "/topic/agencies/"),
    TargetOption("data-analytics", "Data/Analytics", "/topic/analytics/"),
    TargetOption("influencer", "Influencer", "/topic/influencer-marketing/"),
    TargetOption("marketing", "Marketing", "/"),
    TargetOption("ad-tech", "Ad Tech", "/topic/marketing-tech/"),
    TargetOption("cmo-corner", "CMO Corner", "/topic/cmo-corner/"),
]
