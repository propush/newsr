from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from textual.widgets import Input, Static

from newsr.domain import ArticleContent
from newsr.providers.llm import OpenAILLMClient
from newsr.providers.topic import TopicWatchProvider
from newsr.ui import NewsReaderApp, WatchTopicDialogScreen

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.provider_home import provider_home_row_index, provider_home_table
from tests.ui.support.reader import article_pane


def watch_topic_dialog_screen(app: NewsReaderApp) -> WatchTopicDialogScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, WatchTopicDialogScreen):
            return screen
    return None


def test_rebuild_topic_provider_uses_configured_article_retention(app_config, tmp_path) -> None:
    app_config.articles.store = 21
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    app.storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )

    app.rebuild_provider_registry()

    provider = app.providers["topic:openai-policy"]
    assert isinstance(provider, TopicWatchProvider)
    assert provider._max_article_age_days == 21
    app.storage.close()


@pytest.mark.provider_home
def test_ui_provider_home_w_opens_watch_topic_dialog(app_config, tmp_path) -> None:
    app_config.articles.update_schedule = "*/15 * * * *"
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("w")
            await pilot.pause()
            screen = watch_topic_dialog_screen(app)
            assert screen is not None
            assert str(screen.query_one("#watch-topic-dialog-body", Static).content) == (
                "Choose the topic name and an optional cron schedule override for this watched topic. "
                "Leave the schedule blank to use */15 * * * *."
            )
            assert screen.query_one("#watch-topic-name-input", Input).value == ""
            assert screen.query_one("#watch-topic-schedule-input", Input).value == ""
            assert screen.query_one("#watch-topic-schedule-input", Input).placeholder == (
                "Leave blank for */15 * * * *"
            )

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_navigation_still_works_after_watch_topic_dialog(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            table = provider_home_table(app)
            assert table.cursor_row == provider_home_row_index(app, "[ALL]")

            await pilot.press("w", "escape")
            await pilot.pause()
            await pilot.press("down")
            await pilot.pause()

            assert watch_topic_dialog_screen(app) is None
            assert table.cursor_row == provider_home_row_index(app, "BBC News")

    asyncio.run(runner())


def test_ui_reader_navigation_still_works_after_watch_topic_dialog(
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
    monkeypatch.setattr(OpenAILLMClient, "extract_watch_topic", lambda self, title, text: "Test topic")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("w")
            for _ in range(20):
                await pilot.pause()
                if watch_topic_dialog_screen(app) is not None:
                    break
            else:
                raise AssertionError("watch topic dialog did not open")
            await pilot.press("escape")
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


@pytest.mark.provider_home
def test_ui_provider_home_watch_topic_shows_status_for_duplicate_topic(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )
    app.rebuild_provider_registry()
    calls: list[tuple[list[str] | None, bool]] = []
    app._refresh.start = lambda provider_ids=None, *, force=False: calls.append((provider_ids, force))  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_count = len(app.storage.list_providers())
            calls.clear()
            await pilot.press("w")
            await pilot.pause()
            screen = watch_topic_dialog_screen(app)
            assert screen is not None
            screen.query_one("#watch-topic-name-input", Input).value = "  openai   policy  "
            await pilot.press("enter")
            await pilot.pause()
            assert watch_topic_dialog_screen(app) is None
            assert app.status_text == "topic already exists: OpenAI policy"
            assert len(app.storage.list_providers()) == provider_count
            assert calls == []

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_watch_topic_added_during_refresh_starts_due_refresh_after_finish(
    app_config, tmp_path
) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.mark_refresh_completed("bbc")
    app.refresh_in_progress = True
    calls: list[tuple[list[str] | None, bool]] = []
    app._refresh.start = lambda provider_ids=None, *, force=False: calls.append((provider_ids, force))  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("w")
            await pilot.pause()
            screen = watch_topic_dialog_screen(app)
            assert screen is not None
            screen.query_one("#watch-topic-name-input", Input).value = "OpenAI policy"
            await pilot.press("enter")
            await pilot.pause()

            assert watch_topic_dialog_screen(app) is None
            assert app.storage.get_provider("topic:openai-policy") is not None
            assert calls == []

            app._refresh._processed_provider_count = 1
            app._refresh._finish()
            await pilot.pause()

            assert calls == [(["topic:openai-policy"], False)]

    asyncio.run(runner())
