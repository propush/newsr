from __future__ import annotations

import pytest

from newsr.providers.ninetofivegoogle.catalog import (
    BASE_TARGET_OPTIONS,
    TargetOption,
)


class TestTargetOption:
    def test_target_option_frozen(self):
        option = TargetOption("pixel", "Pixel", "/guides/pixel/")
        with pytest.raises(AttributeError):
            option.slug = "new-slug"

    def test_target_option_slots(self):
        option = TargetOption("pixel", "Pixel", "/guides/pixel/")
        # With slots=True, __dict__ should not exist
        assert not hasattr(option, "__dict__")

    def test_target_option_fields(self):
        option = TargetOption("pixel", "Pixel", "/guides/pixel/")
        assert option.slug == "pixel"
        assert option.label == "Pixel"
        assert option.path == "/guides/pixel/"


class TestBaseTargetOptions:
    def test_base_target_options_not_empty(self):
        assert len(BASE_TARGET_OPTIONS) > 0

    def test_base_target_options_count(self):
        assert len(BASE_TARGET_OPTIONS) == 12

    def test_base_target_options_latest(self):
        latest = BASE_TARGET_OPTIONS[0]
        assert latest.slug == "latest"
        assert latest.label == "Latest"
        assert latest.path == "/"

    def test_base_target_options_pixel(self):
        pixel = BASE_TARGET_OPTIONS[1]
        assert pixel.slug == "pixel"
        assert pixel.label == "Pixel"
        assert pixel.path == "/guides/pixel/"

    def test_base_target_options_android(self):
        android = BASE_TARGET_OPTIONS[2]
        assert android.slug == "android"
        assert android.label == "Android"
        assert android.path == "/guides/android/"

    def test_base_target_options_chrome(self):
        chrome = BASE_TARGET_OPTIONS[3]
        assert chrome.slug == "chrome"
        assert chrome.label == "Chrome"
        assert chrome.path == "/guides/chrome/"

    def test_base_target_options_tv(self):
        tv = BASE_TARGET_OPTIONS[4]
        assert tv.slug == "tv"
        assert tv.label == "TV"
        assert tv.path == "/guides/tv/"

    def test_base_target_options_workspace(self):
        workspace = BASE_TARGET_OPTIONS[5]
        assert workspace.slug == "workspace"
        assert workspace.label == "Workspace"
        assert workspace.path == "/guides/workspace/"

    def test_all_options_have_unique_slugs(self):
        slugs = [opt.slug for opt in BASE_TARGET_OPTIONS]
        assert len(slugs) == len(set(slugs))

    def test_all_options_have_slashes_in_paths(self):
        for option in BASE_TARGET_OPTIONS:
            assert option.path.startswith("/")
            assert option.path.endswith("/")
