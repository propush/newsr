from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import patch

from rich.cells import cell_len
from textual.color import Color
from textual.widgets import Markdown, Static

from newsr.domain import ArticleContent
from newsr.ui import OLD_FIDO_THEME, NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import body_source, header_text, url_source


def test_ui_renders_cached_article(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    expected_date = article_content.published_at.astimezone().strftime("%Y-%m-%d %H:%M %Z")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header_widget = app.query_one("#article-header", Static)
            body = body_source(app)
            assert "Article # 1 of 1" in header_text(app)
            assert f"Date : {expected_date}" in header_text(app)
            assert "From : Reporter" not in header_text(app)
            assert "Title: Translated title" in header_text(app)
            assert "Area :" not in header_text(app)
            assert "Reporter @ BBC News " in header_widget.border_title
            assert "world" in header_widget.border_title
            assert "From :" not in header_widget.border_title
            assert "Translated text" in body
            assert url_source(app) == f"URL: {article_content.url}"

    asyncio.run(runner())


def test_ui_reader_only_loads_translated_articles(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    untranslated = ArticleContent(
        article_id="bbc:pending-1",
        provider_id="bbc",
        provider_article_id="pending-1",
        url="https://example.com/bbc/pending-1",
        category="world",
        title="Pending title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Pending source text",
    )
    translated = ArticleContent(
        article_id="bbc:done-1",
        provider_id="bbc",
        provider_article_id="done-1",
        url="https://example.com/bbc/done-1",
        category="technology",
        title="Ready title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Ready source text",
    )
    app.storage.upsert_article_source(untranslated)
    app.storage.upsert_article_source(translated)
    app.storage.update_translation(translated.article_id, "Ready translated title", "Ready translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.articles) == 1
            assert app.current_article is not None
            assert app.current_article.article_id == translated.article_id
            assert "Article # 1 of 1" in header_text(app)
            assert "Ready translated text" in body_source(app)
            assert "Pending source text" not in body_source(app)

    asyncio.run(runner())


def test_ui_truncates_long_article_url_in_middle_to_fit_line(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    long_url = (
        "https://example.com/very/long/path/"
        "with-many-segments/and-even-more-detail/"
        "that-keeps-going/until-it-would-overflow/final-segment"
    )
    app.storage.upsert_article_source(
        article_content.__class__(
            article_id=article_content.article_id,
            provider_id=article_content.provider_id,
            provider_article_id=article_content.provider_article_id,
            url=long_url,
            category=article_content.category,
            title=article_content.title,
            author=article_content.author,
            published_at=article_content.published_at,
            body=article_content.body,
        )
    )
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )

    async def runner() -> None:
        async with app.run_test(size=(50, 20)) as pilot:
            await pilot.pause()
            article_url = app.query_one("#article-url", Static)
            rendered = str(article_url.content)
            assert rendered.startswith("URL: https://")
            assert rendered.endswith("/final-segment")
            assert "…" in rendered
            assert cell_len(rendered) <= article_url.size.width

    asyncio.run(runner())


def test_ui_status_and_resize_refresh_do_not_repaint_article_markdown(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    long_paragraph = " ".join(f"segment-{index}" for index in range(1, 80))
    article = ArticleContent(
        article_id="bbc:repaint-1",
        provider_id="bbc",
        provider_article_id="repaint-1",
        url="https://www.bbc.com/news/repaint-1",
        category="world",
        title="Resize repaint regression",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body=f"{long_paragraph}\n\n{long_paragraph}",
    )
    app.storage.upsert_article_source(article)
    app.storage.update_translation(article.article_id, "Translated repaint title", article.body, "done")

    async def runner() -> None:
        async with app.run_test(size=(72, 20)) as pilot:
            await pilot.pause()
            body_widget = app.query_one("#article-body", Markdown)
            with patch.object(body_widget, "update", wraps=body_widget.update) as update_mock:
                app.set_status("fetching translated repaint article, done 0 of 1")
                app.refresh_view()
                await pilot.pause()
                assert update_mock.call_count == 0

                await pilot.resize_terminal(72, 15)
                await pilot.pause()
                assert update_mock.call_count == 0

    asyncio.run(runner())


def test_ui_hides_author_row_when_author_is_missing(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(
        article_content.__class__(
            article_id=article_content.article_id,
            url=article_content.url,
            category=article_content.category,
            title=article_content.title,
            author=None,
            published_at=article_content.published_at,
            body=article_content.body,
            provider_id=article_content.provider_id,
            provider_article_id=article_content.provider_article_id,
        )
    )
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    expected_date = article_content.published_at.astimezone().strftime("%Y-%m-%d %H:%M %Z")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header_widget = app.query_one("#article-header", Static)
            assert f"Date : {expected_date}" in header_text(app)
            assert "From : bbc" not in header_text(app)
            assert "BBC News " in header_widget.border_title
            assert "world" in header_widget.border_title
            assert "From :" not in header_widget.border_title
            assert "Area :" not in header_text(app)

    asyncio.run(runner())


def test_ui_article_view_falls_back_to_provider_id_when_display_name_is_unknown(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    article = ArticleContent(
        article_id="unknown:test-1",
        provider_id="unknown",
        provider_article_id="test-1",
        url="https://example.com/test-1",
        category="alerts",
        title="Unknown provider title",
        author=None,
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Unknown provider source text",
    )
    app.storage.upsert_article_source(article)
    app.storage.update_translation(article.article_id, "Unknown translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header_widget = app.query_one("#article-header", Static)
            assert "unknown " in header_widget.border_title
            assert "alerts" in header_widget.border_title

    asyncio.run(runner())


def test_ui_article_view_shows_author_with_unknown_provider_id(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    article = ArticleContent(
        article_id="unknown:test-2",
        provider_id="unknown",
        provider_article_id="test-2",
        url="https://example.com/test-2",
        category="alerts",
        title="Unknown provider title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 1, tzinfo=UTC),
        body="Unknown provider source text",
    )
    app.storage.upsert_article_source(article)
    app.storage.update_translation(article.article_id, "Unknown translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header_widget = app.query_one("#article-header", Static)
            assert "Reporter @ unknown " in header_widget.border_title
            assert "alerts" in header_widget.border_title

    asyncio.run(runner())


def test_ui_hides_from_row_when_author_and_provider_are_missing(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(
        article_content.__class__(
            article_id=article_content.article_id,
            url=article_content.url,
            category=article_content.category,
            title=article_content.title,
            author=None,
            published_at=article_content.published_at,
            body=article_content.body,
            provider_id="",
            provider_article_id="",
        )
    )
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header_widget = app.query_one("#article-header", Static)
            assert "From :" not in header_text(app)
            assert header_widget.border_title == "world"

    asyncio.run(runner())


def test_ui_uses_download_date_when_published_date_is_missing(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    article = ArticleContent(
        article_id="test-1",
        url="https://www.bbc.com/news/test-1",
        category="world",
        title="Example title",
        author="Reporter",
        published_at=None,
        body="Paragraph one.\n\nParagraph two.",
    )
    app.storage.upsert_article_source(article)
    app.storage.update_translation(article.article_id, "Translated title", "Translated text", "done")
    stored_article = app.storage.get_article(article.article_id)
    assert stored_article is not None
    expected_date = stored_article.created_at.astimezone().strftime("%Y-%m-%d %H:%M %Z")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert f"Date : {expected_date}" in header_text(app)
            assert "Date : unknown" not in header_text(app)

    asyncio.run(runner())


def test_ui_hides_untranslated_cached_section_pages(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(
        article_content.__class__(
            article_id="world",
            url="https://www.bbc.com/news/world",
            category="world",
            title="World",
            author="Reporter",
            published_at=article_content.published_at,
            body="Teaser text",
        )
    )

    app.load_articles()

    assert app.articles == []


def test_ui_falls_back_to_original_title_without_translated_title(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, None, "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "Title: Example title" in header_text(app)

    asyncio.run(runner())


def test_ui_body_uses_markdown_widget_and_visible_scrollbar(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id,
        "Translated title",
        "\n\n".join(
            [
                "# Heading",
                *[f"- item {index} " + ("detail " * 12) for index in range(40)],
            ]
        ),
        "done",
    )
    app.storage.update_summary(article_content.article_id, "**Brief** summary", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            pane = app.query_one("#article-pane")
            frame = app.query_one("#article-frame")
            article_url = app.query_one("#article-url", Static)
            assert body_source(app).startswith("# Heading")
            assert url_source(app) == f"URL: {article_content.url}"
            assert frame.styles.height.value == 1
            assert pane.styles.height.value == 1
            assert pane.styles.scrollbar_visibility == "visible"
            assert pane.styles.overflow_y == "scroll"
            assert pane.styles.scrollbar_gutter == "stable"
            assert pane.styles.scrollbar_size_vertical == 1
            assert pane.show_vertical_scrollbar is True
            assert pane.max_scroll_y > 0
            assert article_url.styles.height.value == 1
            await pilot.press("s")
            assert body_source(app) == "**Brief** summary"
            assert url_source(app) == f"URL: {article_content.url}"

    asyncio.run(runner())


def test_ui_uses_article_background_for_header_and_compact_header_spacing(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header = app.query_one("#article-header", Static)
            pane = app.query_one("#article-pane")
            body = app.query_one("#article-body", Markdown)
            assert header.styles.background != Color.parse(OLD_FIDO_THEME.surface)
            assert pane.styles.background.a == 0
            assert body.styles.background.a == 0
            assert header.styles.margin.bottom == 0
            assert body.styles.padding.top == 0
            assert header.styles.border_title_align == "left"

    asyncio.run(runner())
