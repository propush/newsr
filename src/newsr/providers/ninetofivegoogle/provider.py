from __future__ import annotations

from urllib.error import HTTPError

from ...cancellation import RefreshCancellation
from ...domain import ArticleContent, ProviderTarget, SectionCandidate
from ..transport import read_text_url
from .catalog import BASE_TARGET_OPTIONS, TargetOption
from .parsing import parse_article_html, parse_section_html
from .urls import NINETOFIVEGOOGLE_ROOT, normalize_target_path


class NineToFiveGoogleProvider:
    provider_id = "ninetofivegoogle"
    display_name = "9to5Google"

    def default_targets(self) -> list[ProviderTarget]:
        return [
            self._target_from_option(option, selected=option.slug in DEFAULT_TARGET_SLUGS)
            for option in BASE_TARGET_OPTIONS
        ]

    def discover_targets(
        self, cancellation: RefreshCancellation | None = None
    ) -> list[ProviderTarget]:
        return self.default_targets()

    def fetch_candidates(
        self, target: ProviderTarget, limit: int, cancellation: RefreshCancellation | None = None
    ) -> list[SectionCandidate]:
        target_path = normalize_target_path(target.payload.get("path", f"/guides/{target.target_key}/"))
        html = self._read_url(f"{NINETOFIVEGOOGLE_ROOT}{target_path}", cancellation)
        candidates = parse_section_html(html, target.label)
        return [
            SectionCandidate(
                article_id=f"{self.provider_id}:{candidate.article_id}",
                provider_id=self.provider_id,
                provider_article_id=candidate.provider_article_id,
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

    def _target_from_option(self, option: TargetOption, *, selected: bool) -> ProviderTarget:
        return ProviderTarget(
            provider_id=self.provider_id,
            target_key=option.slug,
            target_kind="category",
            label=option.label,
            payload={"path": normalize_target_path(option.path)},
            selected=selected,
        )

    @staticmethod
    def _read_url(url: str, cancellation: RefreshCancellation | None = None) -> str:
        try:
            return read_text_url(url, cancellation)
        except HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} fetching {url}") from e


DEFAULT_TARGET_SLUGS = {
    "latest",
    "pixel",
    "android",
    "chrome",
    "tv",
    "workspace",
}
