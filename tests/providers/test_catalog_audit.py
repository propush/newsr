from __future__ import annotations

from pathlib import Path

import pytest

from newsr.providers.registry import build_provider_registry


@pytest.mark.parametrize(
    "provider_id,key,path,fixture",
    [
        ("bbc", "science-environment", "/news/science_and_environment", "section.html"),
        ("9to5mac", "apple-health", "/guides/apple-health/", "ninetofivemac_listing_iphone.html"),
        ("ninetofivegoogle", "workspace", "/guides/google-workspace/", "ninetofivegoogle_listing_pixel.html"),
        ("ninetofivegoogle", "youtube", "/guides/youtube/", "ninetofivegoogle_listing_youtube.html"),
        ("techcrunch", "ai", "/category/artificial-intelligence/", "techcrunch_section.html"),
        ("arstechnica", "gaming", "/gaming/", "arstechnica_section.html"),
        ("hrdive", "compliance", "/topic/legal/", "hrdive_listing_talent.html"),
        ("medcitynews", "artificial-intelligence", "/category/channel/artificial-intelligence/", "medcitynews_listing_health_tech.html"),
        ("hyperallergic", "reviews", "/tag/review/", "hyperallergic_listing_news.html"),
        ("edsurge", "latest", "/", "edsurge_listing_current.html"),
        ("marketingdive", "social-media", "/topic/Social-media-marketing/", "marketingdive_listing_social_media.html"),
        ("marketingdive", "video", "/topic/Video-marketing/", "marketingdive_listing_social_media.html"),
        ("paymentsdive", "technology", "/topic/technology/", "paymentsdive_listing_technology.html"),
        ("tomshardware", "networking", "/networking/news", "tomshardware_listing_networking.html"),
        ("canarymedia", "wind", "/articles/wind", "canarymedia_listing_grid_edge.html"),
        ("lawfare", "congress", "/topics/congress", "lawfare_listing_surveillance_privacy.html"),
        ("infoq", "rust", "/rust/", "infoq_listing_cloud_architecture.html"),
        ("hbr", "technology-and-analytics", "/topic/subject/technology-and-analytics", "hbr_listing_current.html"),
        ("sciencedaily", "space_time", "/news/space_time/", "sciencedaily_listing_computers_math.html"),
        ("thehackernews", "threat-intelligence", "/search/label/Threat%20Intelligence", "thehackernews_section.html"),
    ],
)
def test_verified_targets_fetch_article_candidates(provider_id, key, path, fixture, monkeypatch) -> None:
    provider = build_provider_registry()[provider_id]
    target = next(target for target in provider.default_targets() if target.target_key == key)
    requests: list[str] = []

    def read_url(url, cancellation=None):
        requests.append(url)
        return Path("tests/fixtures", fixture).read_text(encoding="utf-8")

    monkeypatch.setattr(provider, "_read_url", read_url)
    candidates = provider.fetch_candidates(target, limit=2)

    assert len(requests) == 1
    assert requests[0].endswith(path)
    assert candidates
    assert len(candidates) <= 2
    assert all(candidate.provider_id == provider_id for candidate in candidates)
    assert all(candidate.article_id.startswith(provider_id + ":") for candidate in candidates)


def test_all_catalogs_have_unique_identities_and_destinations() -> None:
    for provider in build_provider_registry().values():
        targets = provider.default_targets()
        assert len({target.target_key for target in targets}) == len(targets)
        assert len({target.payload["path"] for target in targets}) == len(targets)
        assert all(target.provider_id == provider.provider_id for target in targets)
        assert all(target.payload["path"].startswith("/") for target in targets)


def test_deloitte_sustainability_uses_its_topic_search_tag(monkeypatch) -> None:
    provider = build_provider_registry()["deloitteinsights"]
    target = next(target for target in provider.default_targets() if target.target_key == "sustainability")
    requests: list[tuple[str, int]] = []

    def read_search_results(search_tag, limit, cancellation=None):
        requests.append((search_tag, limit))
        return Path("tests/fixtures/deloitteinsights_search_business_strategy_growth.json").read_text()

    monkeypatch.setattr(provider, "_read_search_results", read_search_results)
    assert provider.fetch_candidates(target, limit=2)
    assert requests == [("Sustainability", 2)]
    assert target.payload["path"] == "/us/en/insights/topics/sustainability.html"
