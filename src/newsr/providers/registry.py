from __future__ import annotations

from .base import NewsProvider
from .bbc.provider import BBCNewsProvider
from .techcrunch.provider import TechCrunchProvider
from .thehackernews.provider import TheHackerNewsProvider


def build_provider_registry() -> dict[str, NewsProvider]:
    providers = [BBCNewsProvider(), TechCrunchProvider(), TheHackerNewsProvider()]
    return {provider.provider_id: provider for provider in providers}
