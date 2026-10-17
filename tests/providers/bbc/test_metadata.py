from __future__ import annotations

import json
from pathlib import Path

import pytest

from newsr.domain import SectionCandidate
from newsr.providers.bbc.parsing import parse_article_html


def candidate() -> SectionCandidate:
    return SectionCandidate("example", "bbc", "example", "https://www.bbc.com/news/articles/example", "world")


def test_current_bbc_article_uses_publication_date_and_all_structured_authors() -> None:
    html = Path("tests/fixtures/bbc_article_structured_metadata.html").read_text()

    article = parse_article_html(html, candidate())

    assert article.title == "Example news report"
    assert article.author == "Example Reporter, Second Reporter"
    assert article.published_at.isoformat() == "2026-10-13T05:02:44.591000+00:00"
    assert article.body == "The report describes the research findings."


@pytest.mark.parametrize("wrap", [lambda item: item, lambda item: [item], lambda item: {"@graph": [item]}])
def test_bbc_structured_metadata_accepts_article_types_and_graphs(wrap) -> None:
    item = {"@type": ["Thing", "NewsArticle"], "author": {"name": "Reporter"}, "datePublished": "2026-10-13"}
    html = '<script type="application/ld+json">' + json.dumps(wrap(item)) + '</script>'

    article = parse_article_html(html, candidate())

    assert article.author == "Reporter"
    assert article.published_at.isoformat() == "2026-10-13T00:00:00"


@pytest.mark.parametrize("payload", ["broken", "null", "42", '{"@type": {}}', '{"@type":"Organization","author":"Wrong author"}'])
def test_bbc_invalid_or_unrelated_metadata_keeps_author_meta_fallback(payload) -> None:
    html = f'<script type="application/ld+json">{payload}</script><meta name="cXenseParse:author" content="Reporter">'

    article = parse_article_html(html, candidate())

    assert article.author == "Reporter"
    assert article.published_at is None


def test_bbc_invalid_meta_date_falls_back_to_structured_publication_date() -> None:
    html = Path("tests/fixtures/bbc_article_structured_metadata.html").read_text()
    html += '<meta property="article:published_time" content="unavailable">'

    assert parse_article_html(html, candidate()).published_at.isoformat() == "2026-10-13T05:02:44.591000+00:00"
