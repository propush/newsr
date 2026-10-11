from __future__ import annotations

from datetime import datetime, timedelta

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent
from newsr.storage import NewsStorage


class FakeBriefLLM:
    def __init__(
        self,
        *,
        long_first_pass: bool = False,
        report: str | None = None,
        shorten_responses: list[str] | None = None,
        report_responses: list[str] | None = None,
    ) -> None:
        self.long_first_pass = long_first_pass
        self.report = report
        self.shorten_responses = list(shorten_responses or [])
        self.report_responses = list(report_responses or [])
        self.shorten_calls: list[tuple[str, str, int]] = []
        self.report_calls: list[tuple[str, str, int]] = []

    def shorten_brief_notes(
        self,
        system_prompt: str,
        notes: str,
        *,
        max_tokens: int,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        self.shorten_calls.append((system_prompt, notes, max_tokens))
        if self.shorten_responses:
            return self.shorten_responses.pop(0)
        if self.long_first_pass and len(self.shorten_calls) <= 2:
            return "\n".join(
                f"- {'intermediate detail ' * 120}[{number}]"
                for number in _source_numbers(notes)
            )
        return "\n".join(f"- reduced note {number} [{number}]" for number in _source_numbers(notes))

    def synthesize_brief_report(
        self,
        system_prompt: str,
        notes: str,
        *,
        max_tokens: int,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        self.report_calls.append((system_prompt, notes, max_tokens))
        if self.report_responses:
            return self.report_responses.pop(0)
        if self.report is not None:
            return self.report
        return "# Brief\n\n" + "\n".join(
            f"- Final report item {number} [{number}]" for number in _source_numbers(notes)
        )


def _source_numbers(value: str) -> list[int]:
    numbers: list[int] = []
    for part in value.split("[")[1:]:
        raw_number = part.split("]", 1)[0]
        if not raw_number.isdigit():
            continue
        number = int(raw_number)
        if number not in numbers:
            numbers.append(number)
    return numbers or [1]


def seed_article(
    storage: NewsStorage,
    *,
    provider_id: str,
    article_id: str,
    minutes_ago: int,
    summary: str,
    now: datetime,
) -> None:
    published_at = now - timedelta(minutes=minutes_ago)
    content = ArticleContent(
        article_id=f"{provider_id}:{article_id}",
        provider_id=provider_id,
        provider_article_id=article_id,
        url=f"https://example.com/{provider_id}/{article_id}",
        category="news",
        title=f"Title {article_id}",
        author="Reporter",
        published_at=published_at,
        body=f"Body {article_id}",
    )
    storage.upsert_article_source(content)
    storage.update_translation(content.article_id, f"Translated {article_id}", f"Translated body {article_id}", "done")
    storage.update_summary(content.article_id, summary, "done")
