from __future__ import annotations

from ...cancellation import RefreshCancellation
from ...domain import ArticleContent, ProviderTarget, SectionCandidate
from ..transport import read_text_url
from .categories import BASE_CATEGORY_OPTIONS, CategoryOption, merge_category_catalogs
from .parsing import parse_article_html, parse_category_catalog_html, parse_section_html
from .urls import BBC_ROOT


class BBCNewsProvider:
    provider_id = "bbc"
    display_name = "BBC News"

    def default_targets(self) -> list[ProviderTarget]:
        return [self._target_from_option(option, selected=option.slug in DEFAULT_TARGET_SLUGS) for option in BASE_CATEGORY_OPTIONS]

    def discover_targets(
        self, cancellation: RefreshCancellation | None = None
    ) -> list[ProviderTarget]:
        html = self._read_url(f"{BBC_ROOT}/news", cancellation)
        discovered = parse_category_catalog_html(html)
        return [
            self._target_from_option(option, selected=option.slug in DEFAULT_TARGET_SLUGS)
            for option in merge_category_catalogs(BASE_CATEGORY_OPTIONS, discovered)
        ]

    def fetch_candidates(
        self, target: ProviderTarget, limit: int, cancellation: RefreshCancellation | None = None
    ) -> list[SectionCandidate]:
        category = target.payload.get("slug", target.target_key)
        html = self._read_url(f"{BBC_ROOT}/news/{category}", cancellation)
        candidates = parse_section_html(html, category)
        return [
            SectionCandidate(
                article_id=f"{self.provider_id}:{candidate.article_id}",
                provider_id=self.provider_id,
                provider_article_id=candidate.article_id,
                url=candidate.url,
                category=candidate.category,
            )
            for candidate in candidates[:limit]
        ]

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        html = self._read_url(candidate.url, cancellation)
        article = parse_article_html(
            html,
            SectionCandidate(
                article_id=candidate.provider_article_id,
                provider_id=self.provider_id,
                provider_article_id=candidate.provider_article_id,
                url=candidate.url,
                category=candidate.category,
            ),
        )
        return ArticleContent(
            article_id=candidate.article_id,
            provider_id=self.provider_id,
            provider_article_id=candidate.provider_article_id,
            url=article.url,
            category=article.category,
            title=article.title,
            author=article.author,
            published_at=article.published_at,
            body=article.body,
        )

    def _target_from_option(self, option: CategoryOption, *, selected: bool) -> ProviderTarget:
        return ProviderTarget(
            provider_id=self.provider_id,
            target_key=option.slug,
            target_kind="category",
            label=option.label,
            payload={"slug": option.slug},
            selected=selected,
        )

    @staticmethod
    def _read_url(url: str, cancellation: RefreshCancellation | None = None) -> str:
        return read_text_url(url, cancellation)


DEFAULT_TARGET_SLUGS = {
    "world",
    "technology",
    "entertainment_and_arts",
    "business",
}
