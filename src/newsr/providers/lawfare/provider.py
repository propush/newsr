from __future__ import annotations

from ...cancellation import RefreshCancellation
from ...domain import ArticleContent, ProviderTarget, SectionCandidate
from ..transport import read_text_url
from .catalog import BASE_TARGET_OPTIONS, TargetOption
from .parsing import parse_article_html, parse_section_html
from .urls import LAWFARE_ROOT, normalize_target_path


class LawfareProvider:
    provider_id = "lawfare"
    display_name = "Lawfare"

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
        target_path = normalize_target_path(target.payload.get("path", f"/topics/{target.target_key}"))
        html = self._read_url(f"{LAWFARE_ROOT}{target_path}", cancellation)
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
            target_kind="topic",
            label=option.label,
            payload={"path": normalize_target_path(option.path)},
            selected=selected,
        )

    @staticmethod
    def _read_url(url: str, cancellation: RefreshCancellation | None = None) -> str:
        return read_text_url(
            url,
            cancellation,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/135.0.0.0 Safari/537.36"
                ),
            },
        )


DEFAULT_TARGET_SLUGS = {
    "cybersecurity-tech",
    "surveillance-privacy",
}
