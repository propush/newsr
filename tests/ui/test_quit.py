from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from threading import Event

from newsr.domain import ArticleContent, ViewMode
from newsr.ui import NewsReaderApp


class CancellablePipeline:
    def __init__(self) -> None:
        self.started = Event()
        self.cancelled = Event()

    def refresh(
        self,
        provider_ids=None,
        *,
        force=False,
        on_status=None,
        on_article_ready=None,
        cancellation=None,
    ) -> None:  # type: ignore[no-untyped-def]
        del provider_ids, force, on_status, on_article_ready
        self.started.set()
        assert cancellation is not None
        cancellation.cancelled_event.wait(timeout=5)
        self.cancelled.set()


class SlowShutdownPipeline:
    def __init__(self) -> None:
        self.started = Event()
        self.cancelled = Event()
        self.release_refresh = Event()

    def refresh(
        self,
        provider_ids=None,
        *,
        force=False,
        on_status=None,
        on_article_ready=None,
        cancellation=None,
    ) -> None:  # type: ignore[no-untyped-def]
        del provider_ids, force, on_status, on_article_ready
        self.started.set()
        assert cancellation is not None
        cancellation.cancelled_event.wait(timeout=5)
        self.cancelled.set()
        self.release_refresh.wait(timeout=5)


def test_ui_pressing_q_cancels_refresh_before_exit(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.pipeline = CancellablePipeline()  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            for _ in range(20):
                await pilot.pause()
                if app.pipeline.started.is_set():  # type: ignore[union-attr]
                    break
            assert app.pipeline.started.is_set()  # type: ignore[union-attr]
            quit_task = asyncio.create_task(pilot.press("q"))
            await pilot.pause()
            assert app.query_one("#status").content == "Exiting..."
            await quit_task
        assert app.pipeline.cancelled.is_set()  # type: ignore[union-attr]

    asyncio.run(runner())


def test_ui_pressing_q_exits_without_waiting_for_refresh_shutdown(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    pipeline = SlowShutdownPipeline()
    app.pipeline = pipeline  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            for _ in range(100):
                await pilot.pause()
                if pipeline.started.is_set():
                    break
            assert pipeline.started.is_set()
            quit_task = asyncio.create_task(pilot.press("q"))
            for _ in range(100):
                await pilot.pause()
                if quit_task.done():
                    break
            assert pipeline.cancelled.is_set()
            assert quit_task.done()
            pipeline.release_refresh.set()

    asyncio.run(runner())


def test_ui_pressing_q_discards_incomplete_articles(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    completed = ArticleContent(
        article_id="done-1",
        url="https://www.bbc.com/news/done-1",
        category="technology",
        title="Done title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Done source",
    )
    app.storage.upsert_article_source(completed)
    app.storage.complete_translation(completed.article_id, "Done translated", "Done translated body")
    app.storage.complete_summary(completed.article_id, "Done summary")
    app.load_articles()

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.articles) == 1
            assert app.current_article is not None
            assert app.current_article.article_id == "done-1"
            await pilot.press("q")

    asyncio.run(runner())

    storage = app.storage.__class__(storage_path)
    storage.initialize()
    try:
        articles = storage.list_articles()
        state = storage.load_reader_state("[ALL]")
    finally:
        storage.close()

    assert [article.article_id for article in articles] == ["done-1"]
    assert state.article_id == "done-1"


def test_ui_quit_rewrites_stale_saved_incomplete_article_when_it_is_removed(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    completed = ArticleContent(
        article_id="done-1",
        url="https://www.bbc.com/news/done-1",
        category="technology",
        title="Done title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Done source",
    )
    newest_incomplete = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="world",
        title="Newest title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 10, tzinfo=UTC),
        body="Newest source",
    )
    app.storage.upsert_article_source(article_content)
    app.storage.upsert_article_source(completed)
    app.storage.complete_translation(completed.article_id, "Done translated", "Done translated body")
    app.storage.complete_summary(completed.article_id, "Done summary")
    app.storage.upsert_article_source(newest_incomplete)
    app.storage.save_reader_state(
        "[ALL]",
        app.reader_state.__class__(
            article_id=newest_incomplete.article_id,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        ),
    )
    app.load_articles()

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == "done-1"
            await pilot.press("q")

    asyncio.run(runner())

    storage = app.storage.__class__(storage_path)
    storage.initialize()
    try:
        articles = storage.list_articles()
        state = storage.load_reader_state("[ALL]")
    finally:
        storage.close()

    assert [article.article_id for article in articles] == ["done-1"]
    assert state.article_id == "done-1"
