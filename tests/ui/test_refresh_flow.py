from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from threading import Event

from rich.cells import cell_len
from textual.widgets import LoadingIndicator, Static

from newsr.domain import ArticleContent, ViewMode
from newsr.ui import NewsReaderApp

from tests.ui.support.reader import body_source


def status_loading_indicator(app: NewsReaderApp) -> LoadingIndicator:
    return app.query_one("#status-indicator", LoadingIndicator)


class BusyStatusPipeline:
    def __init__(self, status_message: str = "summarizing world-1, done 0 of 1") -> None:
        self.started = Event()
        self.release_refresh = Event()
        self.status_message = status_message

    def refresh(
        self,
        provider_ids=None,
        *,
        force=False,
        on_status=None,
        on_article_ready=None,
        cancellation=None,
    ) -> None:  # type: ignore[no-untyped-def]
        del provider_ids, force, on_article_ready
        on_status(self.status_message)
        self.started.set()
        self.release_refresh.wait(timeout=5)
        on_status("ready")


def seed_translated_articles(app: NewsReaderApp, count: int) -> None:
    for index in range(count):
        article = ArticleContent(
            article_id=f"test-{index + 1}",
            url=f"https://www.bbc.com/news/test-{index + 1}",
            category="world" if index % 2 == 0 else "technology",
            title=f"Title {index + 1}",
            author="Reporter",
            published_at=datetime(2026, 3, 25, 12, index, tzinfo=UTC),
            body=f"Source text {index + 1}",
        )
        app.storage.upsert_article_source(article)
        app.storage.update_translation(
            article.article_id,
            f"Translated title {index + 1}",
            f"Translated text {index + 1}",
            "done",
        )
        app.storage.update_summary(article.article_id, f"Summary {index + 1}", "done")


def test_ui_ignores_download_while_refresh_is_running(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._refresh._run)
        return object()

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]
    app.refresh_in_progress = True

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("d")
            assert app.status_text == "ready"
            assert calls == []

    asyncio.run(runner())


def test_ui_startup_refresh_blocks_extra_download(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._refresh._run)
        return object()

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(calls) == 1
            assert app.refresh_in_progress is True
            await pilot.press("d")
            assert len(calls) == 1
            assert app.status_text == "ready"

    asyncio.run(runner())


def test_ui_startup_refresh_runs_when_cached_articles_exist(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    seed_translated_articles(app, 3)

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._refresh._run)
        return object()

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(calls) == 1
            assert app.refresh_in_progress is True
            assert app.current_article is not None
            assert body_source(app) == "Translated text 1"
            await pilot.press("d")
            assert len(calls) == 1

    asyncio.run(runner())


def test_ui_navigation_does_not_start_extra_refresh_while_startup_refresh_is_running(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    seed_translated_articles(app, 10)

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._refresh._run)
        return object()

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(calls) == 1

            for _ in range(5):
                await pilot.press("right")

            assert app.current_index == 5
            assert len(calls) == 1
            assert app.refresh_in_progress is True

            await pilot.press("right", "left", "right")
            assert len(calls) == 1

    asyncio.run(runner())


def test_ui_does_not_auto_refresh_after_article_list_grows(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    seed_translated_articles(app, 10)

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._refresh._run)
        return object()

    app._refresh._launch_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()

            for _ in range(5):
                await pilot.press("right")

            assert len(calls) == 1
            app.refresh_in_progress = False

            article = ArticleContent(
                article_id="test-11",
                url="https://www.bbc.com/news/test-11",
                category="world",
                title="Title 11",
                author="Reporter",
                published_at=datetime(2026, 3, 25, 12, 10, tzinfo=UTC),
                body="Source text 11",
            )
            app.storage.upsert_article_source(article)
            app.storage.update_translation(article.article_id, "Translated title 11", "Translated text 11", "done")
            app.storage.update_summary(article.article_id, "Summary 11", "done")
            app.load_articles(preferred_article_id=app.current_article.article_id if app.current_article else None)
            await pilot.pause()

            await pilot.press("right")

            assert app.current_index == 6
            assert len(calls) == 1

    asyncio.run(runner())


class BlockingReadyPipeline:
    def __init__(self, app: NewsReaderApp, article: ArticleContent) -> None:
        self.app = app
        self.article = article
        self.ready_emitted = Event()
        self.summary_emitted = Event()
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
        del provider_ids, force
        self.app.storage.upsert_article_source(self.article)
        self.app.storage.update_translation(
            self.article.article_id, "Translated title", "Translated text", "done"
        )
        on_article_ready(self.article.article_id)
        self.ready_emitted.set()
        self.release_refresh.wait(timeout=5)
        self.app.storage.update_summary(self.article.article_id, "Summary text", "done")
        on_article_ready(self.article.article_id)
        self.summary_emitted.set()
        on_status("ready")


def test_ui_shows_first_ready_article_before_refresh_finishes(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    article = ArticleContent(
        article_id="world-1",
        url="https://www.bbc.com/news/world-1",
        category="world",
        title="World article",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Source text",
    )
    pipeline = BlockingReadyPipeline(app, article)
    app.pipeline = pipeline  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            for _ in range(20):
                await pilot.pause()
                if pipeline.ready_emitted.is_set() and app.articles:
                    break
            assert pipeline.ready_emitted.is_set()
            assert app.refresh_in_progress is True
            assert len(app.articles) == 1
            assert app.current_article is not None
            assert app.current_article.article_id == "world-1"
            assert "Translated text" in body_source(app)
            pipeline.release_refresh.set()
            await pilot.pause()

    asyncio.run(runner())


def test_ui_shows_summary_when_it_becomes_available_before_refresh_finishes(
    app_config, tmp_path
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    article = ArticleContent(
        article_id="world-1",
        url="https://www.bbc.com/news/world-1",
        category="world",
        title="World article",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Source text",
    )
    pipeline = BlockingReadyPipeline(app, article)
    app.pipeline = pipeline  # type: ignore[assignment]
    app.reader_state.view_mode = ViewMode.SUMMARY

    async def runner() -> None:
        async with app.run_test() as pilot:
            for _ in range(20):
                await pilot.pause()
                if pipeline.ready_emitted.is_set() and app.current_article is not None:
                    break
            assert app.current_article is not None
            assert "Translated text" in body_source(app)

            pipeline.release_refresh.set()
            for _ in range(20):
                await pilot.pause()
                if pipeline.summary_emitted.is_set():
                    break

            assert pipeline.summary_emitted.is_set()
            assert app.current_article is not None
            assert app.current_article.summary == "Summary text"
            assert body_source(app) == "Summary text"

    asyncio.run(runner())


def test_ui_keeps_current_article_selected_when_new_article_becomes_ready(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Existing translated title", "Existing translation", "done"
    )
    new_article = ArticleContent(
        article_id="technology-1",
        url="https://www.bbc.com/news/technology-1",
        category="technology",
        title="Technology article",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Fresh source text",
    )
    pipeline = BlockingReadyPipeline(app, new_article)
    app.pipeline = pipeline  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id
            await pilot.press("d")
            for _ in range(20):
                await pilot.pause()
                if pipeline.ready_emitted.is_set() and len(app.articles) == 2:
                    break
            assert pipeline.ready_emitted.is_set()
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id
            assert "Existing translation" in body_source(app)
            pipeline.release_refresh.set()
            await pilot.pause()

    asyncio.run(runner())


def test_ui_shows_status_loading_indicator_during_refresh_work(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    pipeline = BusyStatusPipeline()
    app.pipeline = pipeline  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            for _ in range(20):
                await pilot.pause()
                if pipeline.started.is_set():
                    break

            assert pipeline.started.is_set()
            assert app.query_one("#status", Static).content == "summarizing world-1, done 0 of 1"
            assert status_loading_indicator(app).display is True

            pipeline.release_refresh.set()
            for _ in range(20):
                await pilot.pause()
                if app.query_one("#status", Static).content == "ready":
                    break

            assert app.query_one("#status", Static).content == "ready"
            assert status_loading_indicator(app).display is False

    asyncio.run(runner())


def test_ui_truncates_long_refresh_status_to_keep_progress_visible(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    pipeline = BusyStatusPipeline(
        "summarizing provider:section:" + ("very-long-article-id-" * 5) + ", done 12 of 123"
    )
    app.pipeline = pipeline  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test(size=(44, 20)) as pilot:
            for _ in range(20):
                await pilot.pause()
                if pipeline.started.is_set():
                    break

            assert pipeline.started.is_set()
            status_widget = app.query_one("#status", Static)
            status_text = str(status_widget.content)
            assert "done 12 of 123" in status_text
            assert "…" in status_text
            assert cell_len(status_text) <= status_widget.size.width

            pipeline.release_refresh.set()
            for _ in range(20):
                await pilot.pause()
                if str(app.query_one("#status", Static).content) == "ready":
                    break

    asyncio.run(runner())
