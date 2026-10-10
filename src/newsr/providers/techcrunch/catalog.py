from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TopicOption:
    slug: str
    label: str
    path: str


BASE_TOPIC_OPTIONS: tuple[TopicOption, ...] = (
    TopicOption("latest", "Latest", "/latest/"),
    TopicOption("startups", "Startups", "/category/startups/"),
    TopicOption("venture", "Venture", "/category/venture/"),
    TopicOption("ai", "AI", "/category/artificial-intelligence/"),
    TopicOption("security", "Security", "/category/security/"),
    TopicOption("apps", "Apps", "/category/apps/"),
    TopicOption("fintech", "Fintech", "/category/fintech/"),
    TopicOption("enterprise", "Enterprise", "/category/enterprise/"),
    TopicOption("climate", "Climate", "/category/climate/"),
    TopicOption("robotics", "Robotics", "/category/robotics/"),
    TopicOption("government-policy", "Government & Policy", "/category/government-policy/"),
    TopicOption("apple", "Apple", "/tag/apple/"),
    TopicOption("amazon", "Amazon", "/tag/amazon/"),
    TopicOption("biotech-health", "Biotech & Health", "/category/biotech-health/"),
    TopicOption("cloud-computing", "Cloud Computing", "/tag/cloud-computing/"),
    TopicOption("commerce", "Commerce", "/category/commerce/"),
    TopicOption("cryptocurrency", "Crypto", "/category/cryptocurrency/"),
    TopicOption("evs", "EVs", "/tag/evs/"),
    TopicOption("fundraising", "Fundraising", "/category/fundraising/"),
    TopicOption("gadgets", "Gadgets", "/category/gadgets/"),
    TopicOption("gaming", "Gaming", "/category/gaming/"),
    TopicOption("google", "Google", "/tag/google/"),
    TopicOption("hardware", "Hardware", "/category/hardware/"),
    TopicOption("instagram", "Instagram", "/tag/instagram/"),
    TopicOption("layoffs", "Layoffs", "/tag/layoffs/"),
    TopicOption("media-entertainment", "Media & Entertainment", "/category/media-entertainment/"),
    TopicOption("meta", "Meta", "/tag/meta/"),
    TopicOption("microsoft", "Microsoft", "/tag/microsoft/"),
    TopicOption("privacy", "Privacy", "/category/privacy/"),
    TopicOption("social", "Social", "/category/social/"),
    TopicOption("space", "Space", "/category/space/"),
    TopicOption("tiktok", "TikTok", "/tag/tiktok/"),
    TopicOption("transportation", "Transportation", "/category/transportation/"),
)
