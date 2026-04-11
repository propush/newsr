from __future__ import annotations

import json

from ...cancellation import RefreshCancellation
from ...domain import ArticleContent, ProviderTarget, SectionCandidate
from ..transport import newsr_headers, read_text_url
from .catalog import BASE_TARGET_OPTIONS, TargetOption
from .parsing import parse_article_html, parse_search_response
from .urls import DELOITTE_SEARCH_ENDPOINT, normalize_target_path


class DeloitteInsightsProvider:
    provider_id = "deloitteinsights"
    display_name = "Deloitte Insights"

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
        search_tag = target.payload.get("search_tag", target.label)
        payload = self._read_search_results(search_tag, limit, cancellation)
        candidates = parse_search_response(payload, target.label)
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
            payload={
                "path": normalize_target_path(option.path),
                "search_tag": option.search_tag,
            },
            selected=selected,
        )

    @staticmethod
    def _read_url(url: str, cancellation: RefreshCancellation | None = None) -> str:
        return read_text_url(url, cancellation)

    @staticmethod
    def _read_search_results(
        search_tag: str, limit: int, cancellation: RefreshCancellation | None = None
    ) -> str:
        return read_text_url(
            DELOITTE_SEARCH_ENDPOINT,
            cancellation,
            data=json.dumps(_search_payload(search_tag, limit)).encode("utf-8"),
            headers=newsr_headers(
                {
                    "Content-Type": "application/json",
                    "d-target": "elastic",
                }
            ),
            method="POST",
        )


def _search_payload(search_tag: str, limit: int) -> dict[str, object]:
    size = min(max(limit * 6, 50), 100)
    return {
        "query": {
            "bool": {
                "must": [
                    {
                        "terms": {
                            "page-type.keyword": [
                                "insights-article",
                                "insights-multimedia",
                                "insights-research-hubs",
                            ]
                        }
                    },
                    {"match": {"site-name.raw": "us"}},
                    {"match": {"language.raw": "en"}},
                    {
                        "bool": {
                            "should": [
                                {"terms": {"primary-subject.keyword": [search_tag]}},
                                {"terms": {"tag-titles.keyword": [search_tag]}},
                            ]
                        }
                    },
                ]
            }
        },
        "_source": [
            "content-type",
            "date-published",
            "page-description",
            "page-type",
            "primary-subject",
            "promo-title",
            "read-duration",
            "tag-titles",
            "title",
            "url",
        ],
        "from": "0",
        "size": str(size),
    }


DEFAULT_TARGET_SLUGS = {
    "business-strategy-growth",
    "technology-management",
}
