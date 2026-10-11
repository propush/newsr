from __future__ import annotations

import asyncio
import webbrowser
from datetime import UTC, datetime

from textual.widgets import Static

from newsr.domain import ArticleContent
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import article_pane, body_source, url_source
from tests.ui.support.screens import open_link_confirm_screen


def test_ui_pressing_o_requests_confirmation_before_opening_current_article_in_browser(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )

    opened_urls: list[tuple[str, int]] = []

    def fake_open(url: str, new: int = 0) -> bool:
        opened_urls.append((url, new))
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("o")
            confirm = open_link_confirm_screen(app)
            assert confirm is not None
            assert f"URL: {article_content.url}" in confirm.query_one("#open-link-body", Static).content
            assert opened_urls == []
            await pilot.press("enter")
            await pilot.pause()
            assert app.query_one("#status", Static).content == "opened article in browser"

    asyncio.run(runner())

    assert opened_urls == [(article_content.url, 2)]


def test_ui_dismissing_open_link_confirmation_returns_to_article_view(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )

    opened_urls: list[tuple[str, int]] = []
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0: opened_urls.append((url, new)) or True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.provider_home_open is False
            await pilot.press("o")
            await pilot.pause()
            assert open_link_confirm_screen(app) is not None

            await pilot.press("escape")
            await pilot.pause()

            assert open_link_confirm_screen(app) is None
            assert app.provider_home_open is False
            assert getattr(app.focused, "id", None) != "provider-home-table"
            assert body_source(app) == "Translated text"
            assert url_source(app) == f"URL: {article_content.url}"
            assert opened_urls == []

    asyncio.run(runner())


def test_ui_reader_navigation_still_works_after_open_link_confirmation(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    newer_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Newer title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Newer source text",
    )
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(200))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Older translated title", tall_body, "done")
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0: True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("o", "escape")
            await pilot.pause()

            pane = article_pane(app)
            await pilot.press("pagedown")
            await pilot.pause()
            assert pane.scroll_target_y > 0

            await pilot.press("right")
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id

    asyncio.run(runner())


def test_ui_pressing_o_without_current_article_is_ignored(app_config, tmp_path, monkeypatch) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)

    calls: list[str] = []

    def fake_launch_refresh_thread() -> object:
        return object()

    def fake_open(url: str, new: int = 0) -> bool:
        calls.append(url)
        return True

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]
    monkeypatch.setattr(webbrowser, "open", fake_open)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("o")
            assert calls == []
            assert app.query_one("#status", Static).content == "ready"
            assert url_source(app) == ""

    asyncio.run(runner())
