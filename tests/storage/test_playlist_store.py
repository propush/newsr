from __future__ import annotations

from pathlib import Path

from newsr.domain import ArticleContent, PlaylistItem
from newsr.storage import NewsStorage


def test_storage_persists_playlist_order(storage, article_content: ArticleContent) -> None:
    second = ArticleContent(
        article_id="bbc:test-2",
        provider_id="bbc",
        provider_article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="world",
        title="Second",
        author=None,
        published_at=None,
        body="Body",
    )
    storage.upsert_article_source(article_content)
    storage.upsert_article_source(second)
    items = [PlaylistItem(second.article_id, "[ALL]"), PlaylistItem(article_content.article_id, "bbc")]

    storage.save_playlist(items)
    assert storage.load_playlist() == items

    storage.save_playlist(items[1:])
    assert storage.load_playlist() == items[1:]


def test_storage_playlist_skips_deleted_articles(storage, article_content: ArticleContent) -> None:
    storage.upsert_article_source(article_content)
    storage.save_playlist([PlaylistItem("missing", "[ALL]"), PlaylistItem(article_content.article_id, "[ALL]")])

    assert storage.load_playlist() == [PlaylistItem(article_content.article_id, "[ALL]")]


def test_storage_adds_playlist_table_to_existing_database(tmp_path: Path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    first = NewsStorage(storage_path)
    first.initialize()
    first.connection.execute("DROP TABLE playlist")
    first.connection.commit()
    first.close()

    reopened = NewsStorage(storage_path)
    reopened.initialize()
    try:
        tables = {
            row[0]
            for row in reopened.connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert "playlist" in tables
        assert reopened.load_playlist() == []
    finally:
        reopened.close()
