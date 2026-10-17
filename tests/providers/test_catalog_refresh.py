from __future__ import annotations

from pathlib import Path

import pytest

from newsr.providers.registry import build_provider_registry


@pytest.mark.parametrize("provider_id,key,path,fixture,article_id", [
    ("9to5mac", "homepod", "/guides/homepod/", "ninetofivemac_listing_homepod.html", "2026/10/16/example-homepod-report"),
    *[("ninetofivegoogle", key, f"/guides/{slug}/", "ninetofivegoogle_listing_gmail.html", "2026/09/19/example-gmail-report")
      for key, slug in [
          ("pixel-watch", "google-pixel-watch"), ("samsung", "samsung"), ("oneplus", "oneplus"),
          ("oppo", "oppo"), ("xiaomi", "xiaomi"), ("android-tv", "android-tv"),
          ("chromecast", "chromecast"), ("gmail", "gmail"), ("google-meet", "google-meet"),
          ("google-chat", "google-chat"), ("google-calendar", "google-calendar"),
          ("google-keep", "google-keep"), ("google-drive", "google-drive"), ("google-docs", "google-docs"),
      ]],
    *[("tomshardware", key, path + "/news", "tomshardware_listing_headphones.html", "peripherals/gaming-headsets/example-headset-report")
      for key, path in [
          ("routers", "/networking/routers"), ("pc-building", "/desktops/pc-building"),
          ("gaming-laptops", "/laptops/gaming-laptops"), ("ultrabooks", "/laptops/ultrabooks-ultraportables"),
          ("gaming-pcs", "/desktops/gaming-pcs"), ("gaming-monitors", "/monitors/gaming-monitors"),
          ("keyboards", "/peripherals/keyboards"), ("mice", "/peripherals/mice"),
          ("headphones", "/peripherals/headphones-headsets"),
      ]],
    ("sciencedaily", "latest", "/news/", "sciencedaily_listing_latest.html", "releases/2026/10/261015003803"),
    ("sciencedaily", "top-science", "/news/top/science/", "sciencedaily_listing_latest.html", "releases/2026/10/261015003803"),
])
def test_added_sections_route_to_written_article_listings(provider_id, key, path, fixture, article_id, monkeypatch) -> None:
    provider = build_provider_registry()[provider_id]
    target = next(target for target in provider.default_targets() if target.target_key == key)
    requests: list[str] = []

    def read_url(url, cancellation=None):
        requests.append(url)
        return Path("tests/fixtures", fixture).read_text()

    monkeypatch.setattr(provider, "_read_url", read_url)
    candidates = provider.fetch_candidates(target, limit=10)

    assert target.selected is False
    assert len(requests) == 1
    assert requests[0].endswith(path)
    assert [candidate.provider_article_id for candidate in candidates] == [article_id]
    assert candidates[0].article_id == f"{provider_id}:{article_id}"
    assert candidates[0].category == target.label


@pytest.mark.parametrize("provider_id,key,label,path", [
    ("arstechnica", "gadgets", "Tech", "/gadgets/"),
    ("arstechnica", "tech-policy", "Policy", "/tech-policy/"),
    ("sciencedaily", "strange_offbeat", "Strange & Offbeat", "/news/strange_offbeat/"),
    ("infoq", "case-study", "Case Studies", "/case_study/"),
    ("infoq", "designpattern", "Patterns", "/designpattern/"),
    ("infoq", "security", "Security", "/security/"),
    ("hbr", "work-life-balance", "Work-life Balance", "/topic/subject/work_life-balance"),
])
def test_current_labels_and_destinations_keep_existing_keys(provider_id, key, label, path) -> None:
    targets = build_provider_registry()[provider_id].default_targets()
    target = next(target for target in targets if target.target_key == key)

    assert target.label == label
    assert target.payload["path"] == path
