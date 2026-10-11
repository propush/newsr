from __future__ import annotations

from collections.abc import Sequence

from .budget import estimate_token_count, trim_to_budget
from .models import BriefArticle, BriefBatch
from .repair import BriefValidation, format_validation


def format_article(article: BriefArticle, input_budget: int) -> str:
    timestamp = article.published_at or article.created_at
    prefix = (
        f"Source: [{article.number}]\n"
        f"Provider: {article.provider_name}\n"
        f"Title: {article.title}\n"
        f"Published: {timestamp.astimezone().strftime('%Y-%m-%d %H:%M %Z')}\n"
        "Summary:\n"
    )
    remaining = max(1, input_budget - estimate_token_count(prefix) - 1)
    return prefix + trim_to_budget(article.summary, remaining)


def format_fallback_article(article: BriefArticle, input_budget: int) -> str:
    summary = trim_to_budget(article.summary, input_budget)
    return f"- {article.title}: {summary} [{article.number}]"


def format_source_catalog(articles: Sequence[BriefArticle], input_budget: int) -> str:
    entries: list[str] = []
    for article in articles:
        entry = format_article(article, max(1, input_budget // max(1, len(articles))))
        entries.append(entry)
    return trim_to_budget("\n\n".join(entries), input_budget)


def batch_texts(values: Sequence[str], input_budget: int) -> list[str]:
    batches: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for value in values:
        text = trim_to_budget(value, input_budget)
        token_count = estimate_token_count(text)
        separator_tokens = 1 if current else 0
        if current and current_tokens + separator_tokens + token_count > input_budget:
            batches.append("\n\n".join(current))
            current = []
            current_tokens = 0
        current.append(text)
        current_tokens += token_count + separator_tokens
    if current:
        batches.append("\n\n".join(current))
    return batches


def article_batches(
    values: Sequence[str],
    articles: Sequence[BriefArticle],
    input_budget: int,
) -> list[BriefBatch]:
    batches: list[BriefBatch] = []
    current: list[str] = []
    current_articles: list[BriefArticle] = []
    current_numbers: set[int] = set()
    current_tokens = 0
    for value, article in zip(values, articles, strict=True):
        text = trim_to_budget(value, input_budget)
        token_count = estimate_token_count(text)
        separator_tokens = 1 if current else 0
        if current and current_tokens + separator_tokens + token_count > input_budget:
            batches.append(
                BriefBatch(
                    text="\n\n".join(current),
                    article_numbers=frozenset(current_numbers),
                    articles=tuple(current_articles),
                )
            )
            current = []
            current_articles = []
            current_numbers = set()
            current_tokens = 0
            separator_tokens = 0
        current.append(text)
        current_articles.append(article)
        current_numbers.add(article.number)
        current_tokens += token_count + separator_tokens
    if current:
        batches.append(
            BriefBatch(
                text="\n\n".join(current),
                article_numbers=frozenset(current_numbers),
                articles=tuple(current_articles),
            )
        )
    return batches


def repair_content(
    *,
    source_text: str,
    draft_text: str,
    validation: BriefValidation,
    input_budget: int,
) -> str:
    content = (
        f"Source material:\n{source_text}\n\n"
        f"Draft notes:\n{draft_text}\n\n"
        f"Validation problems:\n{format_validation(validation)}"
    )
    return trim_to_budget(content, input_budget)


def final_repair_content(
    *,
    articles: Sequence[BriefArticle],
    notes: Sequence[str],
    draft_report: str,
    validation: BriefValidation,
    input_budget: int,
) -> str:
    source_budget = max(1, input_budget // 2)
    source_catalog = format_source_catalog(articles, source_budget)
    content = (
        f"Source articles:\n{source_catalog}\n\n"
        f"Compressed notes:\n{trim_to_budget(chr(10).join(notes), max(1, input_budget // 5))}\n\n"
        f"Draft brief:\n{draft_report}\n\n"
        f"Validation problems:\n{format_validation(validation)}"
    )
    return trim_to_budget(content, input_budget)
