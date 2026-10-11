from __future__ import annotations

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent, ProviderTarget, SectionCandidate


class FakeProvider:
    provider_id = "bbc"
    display_name = "BBC News"

    def default_targets(self) -> list[ProviderTarget]:
        raise AssertionError("default_targets is not used in pipeline tests")

    def discover_targets(
        self, cancellation: RefreshCancellation | None = None
    ) -> list[ProviderTarget]:
        raise AssertionError("discover_targets is not used in pipeline tests")

    def fetch_candidates(
        self, target: ProviderTarget, limit: int, cancellation: RefreshCancellation | None = None
    ) -> list[SectionCandidate]:
        category = target.payload.get("slug", target.target_key)
        return [
            SectionCandidate(
                article_id=f"bbc:{category}-1",
                provider_id="bbc",
                provider_article_id=f"{category}-1",
                url=f"https://www.bbc.com/news/{category}-1",
                category=category,
            )
        ]

    def fetch_article(
        self, candidate: SectionCandidate, cancellation: RefreshCancellation | None = None
    ) -> ArticleContent:
        return ArticleContent(
            article_id=candidate.article_id,
            provider_id=candidate.provider_id,
            provider_article_id=candidate.provider_article_id,
            url=candidate.url,
            category=candidate.category,
            title=f"{candidate.category} article",
            author="Reporter",
            published_at=None,
            body="source body",
        )


class FakeLLM:
    def classify_article_categories(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> tuple[str, ...]:
        return ("TECHNOLOGIES",)

    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        return f"translated {article_title}"

    def translate(
        self,
        article_title: str,
        source_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        return f"translated {source_text}"

    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        return f"summary {translated_text}"


class RecordingLLM:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def classify_article_categories(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> tuple[str, ...]:
        self.calls.append(f"classify:{article_title}")
        return ("TECHNOLOGIES",)

    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        self.calls.append(f"translate_title:{article_title}")
        return f"translated {article_title}"

    def translate(
        self,
        article_title: str,
        source_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.calls.append(f"translate:{article_title}")
        return f"translated {source_text}"

    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.calls.append(f"summarize:{article_title}")
        return f"summary {translated_text}"
