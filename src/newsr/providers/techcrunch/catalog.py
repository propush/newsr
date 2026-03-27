from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TopicOption:
    slug: str
    label: str
    path: str


BASE_TOPIC_OPTIONS: tuple[TopicOption, ...] = (
    TopicOption(slug="latest", label="Latest", path="/latest/"),
    TopicOption(slug="startups", label="Startups", path="/category/startups/"),
    TopicOption(slug="venture", label="Venture", path="/category/venture/"),
    TopicOption(slug="ai", label="AI", path="/tag/ai/"),
    TopicOption(slug="security", label="Security", path="/category/security/"),
    TopicOption(slug="apps", label="Apps", path="/category/apps/"),
    TopicOption(slug="fintech", label="Fintech", path="/category/fintech/"),
    TopicOption(slug="enterprise", label="Enterprise", path="/category/enterprise/"),
    TopicOption(slug="climate", label="Climate", path="/category/climate/"),
    TopicOption(slug="robotics", label="Robotics", path="/category/robotics/"),
    TopicOption(
        slug="government-policy",
        label="Government & Policy",
        path="/category/government-policy/",
    ),
)
