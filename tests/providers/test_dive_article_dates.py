from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from newsr.domain import SectionCandidate


@pytest.mark.parametrize("provider_id,time", [("hrdive", "16:51:00"), ("marketingdive", "11:59:00")])
def test_dive_articles_read_sailthru_publication_date(provider_id, time) -> None:
    parsing = importlib.import_module(f"newsr.providers.{provider_id}.parsing")
    html = Path(f"tests/fixtures/{provider_id}_article_sailthru.html").read_text()
    candidate = SectionCandidate("example", provider_id, "example", "https://example.com/news/example/", "Latest")

    article = parsing.parse_article_html(html, candidate)

    assert article.published_at.isoformat() == f"2026-10-15T{time}"
    assert article.author == "Example Reporter"
    assert article.body.startswith("The report explains")


@pytest.mark.parametrize("provider_id", ["hrdive", "marketingdive"])
@pytest.mark.parametrize("metadata,expected", [
    ('<meta property="article:published_time" content="2026-10-14T10:00:00Z"><meta name="sailthru.date" content="2026-10-15">', "2026-10-14T10:00:00+00:00"),
    ('<meta property="article:published_time" content="invalid"><meta name="sailthru.date" content="2026-10-15T12:00:00">', "2026-10-15T12:00:00"),
    ('<meta name="sailthru.date" content="invalid"><meta name="date" content="2026-10-15">', "2026-10-15T00:00:00"),
    ('<meta name="date" content="invalid"><time datetime="2026-10-15T13:00:00Z"></time>', "2026-10-15T13:00:00+00:00"),
    ('<meta name="date" content="invalid"><time datetime="invalid"></time>', None),
])
def test_dive_date_fallbacks_preserve_articles_with_invalid_metadata(provider_id, metadata, expected) -> None:
    parsing = importlib.import_module(f"newsr.providers.{provider_id}.parsing")
    candidate = SectionCandidate("example", provider_id, "example", "https://example.com/news/example/", "Latest")

    published_at = parsing.parse_article_html(metadata, candidate).published_at

    assert (published_at.isoformat() if published_at else None) == expected
