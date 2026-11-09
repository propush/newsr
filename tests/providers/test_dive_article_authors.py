from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from newsr.domain import SectionCandidate


@pytest.mark.parametrize("provider_id", ["hrdive", "marketingdive"])
def test_dive_contributor_bylines_use_sailthru_author_over_share_links(provider_id) -> None:
    parsing = importlib.import_module(f"newsr.providers.{provider_id}.parsing")
    html = Path(f"tests/fixtures/{provider_id}_article_contributor.html").read_text()
    candidate = SectionCandidate("example", provider_id, "example", "https://example.com/news/example/", "Latest")

    article = parsing.parse_article_html(html, candidate)

    assert article.author == "Example Contributor"
    assert article.published_at.isoformat() == "2026-11-06T13:51:00"
    assert article.body.startswith("The analysis explains")
