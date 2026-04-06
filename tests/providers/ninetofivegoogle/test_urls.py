from __future__ import annotations

import pytest

from newsr.providers.ninetofivegoogle.urls import (
    NINETOFIVEGOOGLE_ROOT,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
)


class TestNormalizeTargetPath:
    def test_empty_path(self):
        assert normalize_target_path("") == "/"

    def test_whitespace_path(self):
        assert normalize_target_path("   ") == "/"

    def test_root_path(self):
        assert normalize_target_path("/") == "/"

    def test_path_without_leading_slash(self):
        assert normalize_target_path("guides/pixel") == "/guides/pixel/"

    def test_path_with_trailing_slash(self):
        assert normalize_target_path("/guides/pixel/") == "/guides/pixel/"

    def test_path_without_trailing_slash(self):
        assert normalize_target_path("/guides/pixel") == "/guides/pixel/"

    def test_complex_path(self):
        assert normalize_target_path("/guides/android/2024/") == "/guides/android/2024/"


class TestNormalizeUrl:
    def test_absolute_url(self):
        result = normalize_url("https://9to5google.com/guides/pixel/")
        assert result == "https://9to5google.com/guides/pixel/"

    def test_relative_url(self):
        result = normalize_url("/guides/pixel/")
        assert result == "https://9to5google.com/guides/pixel/"

    def test_relative_url_no_leading_slash(self):
        result = normalize_url("guides/pixel/")
        assert result == "https://9to5google.com/guides/pixel/"

    def test_www_host(self):
        result = normalize_url("https://www.9to5google.com/guides/pixel/")
        assert result == "https://9to5google.com/guides/pixel/"

    def test_path_without_trailing_slash(self):
        result = normalize_url("/guides/pixel")
        assert result == "https://9to5google.com/guides/pixel/"


class TestIsArticleUrl:
    def test_valid_article_url(self):
        url = "https://9to5google.com/2024/01/15/google-pixel-8-pro-review/"
        assert is_article_url(url) is True

    def test_valid_article_url_with_trailing_slash(self):
        url = "https://9to5google.com/2024/01/15/google-pixel-8-pro-review"
        assert is_article_url(url) is True

    def test_invalid_url_wrong_host(self):
        url = "https://9to5mac.com/2024/01/15/some-article/"
        assert is_article_url(url) is False

    def test_invalid_url_not_date_pattern(self):
        url = "https://9to5google.com/guides/pixel/"
        assert is_article_url(url) is False

    def test_invalid_url_homepage(self):
        url = "https://9to5google.com/"
        assert is_article_url(url) is False

    def test_invalid_url_guides_path(self):
        url = "https://9to5google.com/guides/"
        assert is_article_url(url) is False

    def test_article_url_missing_trailing_slash(self):
        url = "https://9to5google.com/2024/01/15/pixel-review"
        assert is_article_url(url) is True


class TestArticleIdFromUrl:
    def test_extract_article_id(self):
        url = "https://9to5google.com/2024/01/15/google-pixel-8-pro-review/"
        result = article_id_from_url(url)
        assert result == "2024/01/15/google-pixel-8-pro-review"

    def test_extract_article_id_no_trailing_slash(self):
        url = "https://9to5google.com/2024/01/15/google-pixel-8-pro-review"
        result = article_id_from_url(url)
        assert result == "2024/01/15/google-pixel-8-pro-review"

    def test_article_id_from_relative_url(self):
        url = "/2024/01/15/google-pixel-8-pro-review/"
        result = article_id_from_url(url)
        assert result == "2024/01/15/google-pixel-8-pro-review"
