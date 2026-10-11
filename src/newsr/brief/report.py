from __future__ import annotations

import re
from collections.abc import Sequence

from .formatting import format_fallback_article
from .models import BriefArticle, BriefOptions, BriefPeriod
from .repair import (
    SOURCE_REF_RE,
    reference_numbers,
    remove_invalid_references,
    remove_unreferenced_statement_lines,
)


def empty_report(options: BriefOptions) -> str:
    period = {
        BriefPeriod.LAST_24H: "last 24 hours",
        BriefPeriod.LAST_WEEK: "last week",
        BriefPeriod.ALL_UNREAD: "all unread articles",
    }[options.period]
    return f"# Brief\n\nNo completed article summaries were found for {period}."


def fallback_brief_text(
    text: str,
    required_numbers: frozenset[int],
    articles: Sequence[BriefArticle],
) -> str:
    sanitized = remove_unreferenced_statement_lines(
        remove_invalid_references(text, required_numbers),
        required_numbers,
    ).strip()
    cited_numbers = reference_numbers(sanitized) & required_numbers
    missing_numbers = sorted(required_numbers - cited_numbers)
    if not missing_numbers:
        return sanitized

    fallback_lines = _fallback_lines(missing_numbers, articles)
    if not fallback_lines:
        return sanitized

    if sanitized:
        return f"{sanitized}\n\n## Additional articles\n\n" + "\n".join(fallback_lines)
    return "# Brief\n\n" + "\n".join(fallback_lines)


def _fallback_lines(
    missing_numbers: Sequence[int],
    articles: Sequence[BriefArticle],
) -> list[str]:
    articles_by_number = {article.number: article for article in articles}
    lines: list[str] = []
    for number in missing_numbers:
        article = articles_by_number.get(number)
        if article is None:
            lines.append(f"- Source [{number}]")
            continue
        lines.append(format_fallback_article(article, 80))
    return lines


def renumber_article_references(
    report: str,
    articles: Sequence[BriefArticle],
) -> tuple[str, list[BriefArticle]]:
    if not articles:
        return report, []

    articles_by_number = {article.number: article for article in articles}
    display_by_source_number: dict[int, int] = {}
    cited_articles: list[BriefArticle] = []
    next_display_number = 1

    def replace_reference(match: re.Match[str]) -> str:
        nonlocal next_display_number

        source_number = int(match.group("number"))
        article = articles_by_number.get(source_number)
        if article is None:
            return match.group(0)

        display_number = display_by_source_number.get(source_number)
        if display_number is None:
            display_number = next_display_number
            display_by_source_number[source_number] = display_number
            cited_articles.append(renumber_article(article, display_number))
            next_display_number += 1
        return f"[{display_number}]"

    return SOURCE_REF_RE.sub(replace_reference, report), cited_articles


def renumber_article(article: BriefArticle, number: int) -> BriefArticle:
    return BriefArticle(
        number=number,
        article_id=article.article_id,
        provider_id=article.provider_id,
        provider_name=article.provider_name,
        title=article.title,
        summary=article.summary,
        published_at=article.published_at,
        created_at=article.created_at,
    )


def append_statistics(
    report: str,
    articles: Sequence[BriefArticle],
    provider_ids: Sequence[str],
) -> str:
    counts_by_provider: dict[str, int] = {}
    names_by_provider: dict[str, str] = {}
    for article in articles:
        counts_by_provider[article.provider_id] = (
            counts_by_provider.get(article.provider_id, 0) + 1
        )
        names_by_provider.setdefault(article.provider_id, article.provider_name)

    lines = [
        f"{names_by_provider[provider_id]}: {counts_by_provider[provider_id]}"
        for provider_id in provider_ids
        if provider_id in counts_by_provider
    ]
    if not lines:
        return report
    return f"{report.rstrip()}\n\n## Statistics\n\n" + "\n\n".join(lines)
