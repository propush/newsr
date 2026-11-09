from __future__ import annotations

from datetime import UTC, datetime

from newsr.brief import BriefArticle
from newsr.brief.formatting import note_batches


def _article(number: int) -> BriefArticle:
    created_at = datetime(2026, 5, 18, 12, 0, tzinfo=UTC)
    return BriefArticle(
        number=number,
        article_id=f"bbc:item-{number}",
        provider_id="bbc",
        provider_name="BBC News",
        title=f"Title {number}",
        summary=f"Summary {number}",
        published_at=created_at,
        created_at=created_at,
    )


def test_note_batches_keep_markers_that_trimming_cuts_off() -> None:
    articles = [_article(1), _article(2)]
    long_note = f"- {'detail ' * 100}[1]"

    batches = note_batches([long_note, "- short note [2]"], articles, 40)

    assert "[1]" not in batches[0].text
    assert batches[0].article_numbers == frozenset({1})
    assert batches[0].articles == (articles[0],)
    assert batches[1].article_numbers == frozenset({2})
    assert batches[1].articles == (articles[1],)


def test_note_batches_group_notes_and_ignore_unknown_markers() -> None:
    articles = [_article(1), _article(2), _article(3)]

    batches = note_batches(["- one [1]", "- two [2] [9]", "- three [3]"], articles, 1000)

    assert len(batches) == 1
    assert batches[0].text == "- one [1]\n\n- two [2] [9]\n\n- three [3]"
    assert batches[0].article_numbers == frozenset({1, 2, 3})
    assert batches[0].articles == tuple(articles)
