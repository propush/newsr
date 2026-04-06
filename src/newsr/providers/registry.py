from __future__ import annotations

from .arstechnica.provider import ArsTechnicaProvider
from .base import NewsProvider
from .canarymedia.provider import CanaryMediaProvider
from .edsurge.provider import EdSurgeProvider
from .bbc.provider import BBCNewsProvider
from .deloitteinsights.provider import DeloitteInsightsProvider
from .hrdive.provider import HRDiveProvider
from .hbr.provider import HBRProvider
from .hyperallergic.provider import HyperallergicProvider
from .infoq.provider import InfoQProvider
from .lawfare.provider import LawfareProvider
from .marketingdive.provider import MarketingDiveProvider
from .medcitynews.provider import MedCityNewsProvider
from .ninetofivemac.provider import NineToFiveMacProvider
from .ninetofivegoogle.provider import NineToFiveGoogleProvider
from .sciencedaily.provider import ScienceDailyProvider
from .techcrunch.provider import TechCrunchProvider
from .thehackernews.provider import TheHackerNewsProvider
from .tomshardware.provider import TomsHardwareProvider


def build_provider_registry() -> dict[str, NewsProvider]:
    providers = [
        BBCNewsProvider(),
        NineToFiveMacProvider(),
        NineToFiveGoogleProvider(),
        TechCrunchProvider(),
        TheHackerNewsProvider(),
        ArsTechnicaProvider(),
        HRDiveProvider(),
        MedCityNewsProvider(),
        HyperallergicProvider(),
        EdSurgeProvider(),
        MarketingDiveProvider(),
        TomsHardwareProvider(),
        CanaryMediaProvider(),
        LawfareProvider(),
        InfoQProvider(),
        DeloitteInsightsProvider(),
        HBRProvider(),
        ScienceDailyProvider(),
    ]
    return {provider.provider_id: provider for provider in providers}
