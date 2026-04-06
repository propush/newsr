from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from urllib.request import Request

from newsr.cancellation import RefreshCancellation, RefreshCancelled, RefreshTimedOut
from newsr.domain import ProviderTarget, SectionCandidate
from newsr.providers.ninetofivegoogle.provider import (
    NineToFiveGoogleProvider,
    DEFAULT_TARGET_SLUGS,
)
from newsr.providers.ninetofivegoogle.catalog import BASE_TARGET_OPTIONS


class TestDefaultTargets:
    def test_returns_expected_count(self):
        provider = NineToFiveGoogleProvider()
        targets = provider.default_targets()
        assert len(targets) == len(BASE_TARGET_OPTIONS)

    def test_has_correct_default_selected_slugs(self):
        provider = NineToFiveGoogleProvider()
        targets = provider.default_targets()
        selected = [t.target_key for t in targets if t.selected]
        assert set(selected) == DEFAULT_TARGET_SLUGS

    def test_target_structure(self):
        provider = NineToFiveGoogleProvider()
        targets = provider.default_targets()
        latest = next(t for t in targets if t.target_key == "latest")
        assert latest.provider_id == "ninetofivegoogle"
        assert latest.target_kind == "category"
        assert latest.label == "Latest"
        assert latest.payload == {"path": "/"}


class TestDiscoverTargets:
    def test_returns_same_as_default_targets(self):
        provider = NineToFiveGoogleProvider()
        targets1 = provider.default_targets()
        targets2 = provider.discover_targets()
        assert len(targets1) == len(targets2)
        for t1, t2 in zip(targets1, targets2):
            assert t1.target_key == t2.target_key
            assert t1.label == t2.label


class TestFetchCandidates:
    def test_fetches_candidates_with_limit(self):
        provider = NineToFiveGoogleProvider()
        target = ProviderTarget(
            provider_id="ninetofivegoogle",
            target_key="pixel",
            target_kind="category",
            label="Pixel",
            payload={"path": "/guides/pixel/"},
            selected=False,
        )

        html = """
        <html>
        <body>
            <main>
                <div class="article-list">
                    <div class="article-item">
                        <a href="/2024/01/01/article1/">Article 1</a>
                    </div>
                    <div class="article-item">
                        <a href="/2024/01/02/article2/">Article 2</a>
                    </div>
                    <div class="article-item">
                        <a href="/2024/01/03/article3/">Article 3</a>
                    </div>
                </div>
            </main>
        </body>
        </html>
        """

        with patch.object(provider, '_read_url', return_value=html):
            candidates = provider.fetch_candidates(target, limit=2)
            assert len(candidates) == 2
            assert candidates[0].provider_article_id == "2024/01/01/article1"
            assert candidates[1].provider_article_id == "2024/01/02/article2"

    def test_cancellation_raises_before_fetch(self):
        provider = NineToFiveGoogleProvider()
        target = ProviderTarget(
            provider_id="ninetofivegoogle",
            target_key="pixel",
            target_kind="category",
            label="Pixel",
            payload={"path": "/guides/pixel/"},
            selected=False,
        )

        cancellation = RefreshCancellation()
        cancellation.cancel()

        with pytest.raises(RefreshCancelled):
            provider.fetch_candidates(target, limit=10, cancellation=cancellation)


class TestFetchArticle:
    def test_fetches_article_content(self):
        provider = NineToFiveGoogleProvider()
        candidate = SectionCandidate(
            article_id="ninetofivegoogle:2024/01/01/article1",
            provider_id="ninetofivegoogle",
            provider_article_id="2024/01/01/article1",
            url="https://9to5google.com/2024/01/01/article1/",
            category="Pixel",
        )

        html = """
        <html>
        <head>
            <meta property="og:title" content="Test Article Title">
            <meta name="author" content="Test Author">
            <meta property="article:published_time" content="2024-01-01T12:00:00Z">
        </head>
        <body>
            <div id="content">
                <h1 class="h1">Test Article Title</h1>
                <div class="post-meta">
                    <span class="author-name">Test Author</span>
                </div>
                <div class="container med post-content">
                    <p>This is the article body content.</p>
                </div>
            </div>
        </body>
        </html>
        """

        with patch.object(provider, '_read_url', return_value=html):
            article = provider.fetch_article(candidate)
            assert article.title == "Test Article Title"
            assert article.author == "Test Author"
            assert article.published_at is not None
            assert article.published_at.year == 2024
            assert "article body content" in article.body

    def test_cancellation_raises_before_fetch(self):
        provider = NineToFiveGoogleProvider()
        candidate = SectionCandidate(
            article_id="ninetofivegoogle:2024/01/01/article1",
            provider_id="ninetofivegoogle",
            provider_article_id="2024/01/01/article1",
            url="https://9to5google.com/2024/01/01/article1/",
            category="Pixel",
        )

        cancellation = RefreshCancellation()
        cancellation.cancel()

        with pytest.raises(RefreshCancelled):
            provider.fetch_article(candidate, cancellation=cancellation)


class TestReadUrl:
    def test_reads_url_successfully(self):
        provider = NineToFiveGoogleProvider()
        html = "<html><body>Test</body></html>"

        with patch('newsr.providers.ninetofivegoogle.provider.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = lambda self: mock_response
            mock_response.__exit__ = lambda self, *args: None
            mock_response.read = lambda: html.encode('utf-8')
            mock_urlopen.return_value = mock_response

            result = provider._read_url("https://9to5google.com/test/")
            assert result == html

    def test_http_error_raises(self):
        provider = NineToFiveGoogleProvider()

        with patch('newsr.providers.ninetofivegoogle.provider.urlopen') as mock_urlopen:
            from urllib.error import HTTPError

            mock_urlopen.side_effect = HTTPError(
                url="https://9to5google.com/not-found/",
                hdrs={},
                code=404,
                msg="Not Found",
                fp=None
            )

            with pytest.raises(RuntimeError) as exc_info:
                provider._read_url("https://9to5google.com/not-found/")

            assert "HTTP 404" in str(exc_info.value)
            assert "not-found" in str(exc_info.value)

    def test_http_500_error_raises(self):
        provider = NineToFiveGoogleProvider()

        with patch('newsr.providers.ninetofivegoogle.provider.urlopen') as mock_urlopen:
            from urllib.error import HTTPError

            mock_urlopen.side_effect = HTTPError(
                url="https://9to5google.com/error/",
                hdrs={},
                code=500,
                msg="Internal Server Error",
                fp=None
            )

            with pytest.raises(RuntimeError):
                provider._read_url("https://9to5google.com/error/")
