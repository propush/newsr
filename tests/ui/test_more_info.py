from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from threading import Event

from textual.widgets import LoadingIndicator, Static

from newsr.cancellation import RefreshCancellation
from newsr.domain import ArticleContent, ViewMode
from newsr.providers.search import SearchResult
from newsr.ui import NewsReaderApp

from tests.ui.support.fakes import FakeMoreInfoLLM, FakeSearchClient
from tests.ui.support.reader import body_source
from tests.ui.support.screens import more_info_body, more_info_screen


def more_info_pane(app: NewsReaderApp):
    screen = more_info_screen(app)
    assert screen is not None
    return screen.query_one("#more-info-pane")


def more_info_loading_indicator(app: NewsReaderApp) -> LoadingIndicator:
    screen = more_info_screen(app)
    assert screen is not None
    return screen.query_one("#more-info-loading", LoadingIndicator)


class BlockingQueryLLM:
    def __init__(self) -> None:
        self.started = Event()
        self.cancelled = Event()

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        return None

    def build_search_query(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        assert cancellation is not None
        self.started.set()
        cancellation.cancelled_event.wait(timeout=5)
        if cancellation.is_cancelled:
            self.cancelled.set()
        cancellation.raise_if_cancelled()
        return "unused"

    def synthesize_more_info(
        self,
        article_title: str,
        article_text: str,
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        raise AssertionError("synthesize_more_info should not run after cancellation")


def test_ui_opens_more_info_overlay_and_escape_restores_summary_mode(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    app.llm_client = FakeMoreInfoLLM(responses=["Extra context"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            assert body_source(app) == "Summary text"

            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                screen = more_info_screen(app)
                if screen is not None and "Extra context" in more_info_body(app):
                    break

            screen = more_info_screen(app)
            assert screen is not None
            assert "State: ready" in screen.query_one("#more-info-header", Static).content
            assert more_info_body(app) == "Extra context"

            await pilot.press("escape")
            await pilot.pause()

            assert more_info_screen(app) is None
            assert app.reader_state.view_mode == ViewMode.SUMMARY
            assert body_source(app) == "Summary text"

    asyncio.run(runner())


def test_ui_more_info_refreshes_when_m_is_pressed_again(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeMoreInfoLLM(responses=["Extra context 1", "Extra context 2"])
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                if more_info_screen(app) is not None and more_info_body(app) == "Extra context 1":
                    break

            assert more_info_body(app) == "Extra context 1"

            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                if more_info_body(app) == "Extra context 2":
                    break

            assert more_info_body(app) == "Extra context 2"
            assert len(llm.synthesis_calls) == 2

    asyncio.run(runner())


def test_ui_more_info_space_pagedown_and_b_pageup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    tall_more_info = "\n\n".join(f"Background paragraph {index}" for index in range(200))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.llm_client = FakeMoreInfoLLM(responses=[tall_more_info])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                screen = more_info_screen(app)
                if screen is not None and more_info_body(app) == tall_more_info:
                    break

            pane = more_info_pane(app)
            assert pane.scroll_target_y == 0

            await pilot.press("space")
            await pilot.pause()
            after_page_down = pane.scroll_target_y
            assert after_page_down > 0

            await pilot.press("b")
            await pilot.pause()
            assert pane.scroll_target_y < after_page_down

    asyncio.run(runner())


def test_ui_more_info_search_uses_original_article_subject(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeMoreInfoLLM(responses=["Extra context"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                if more_info_screen(app) is not None and more_info_body(app) == "Extra context":
                    break

            assert llm.query_calls == [("Example title", "Paragraph one.\n\nParagraph two.")]
            assert llm.synthesis_calls[0][0] == "Example title"
            assert llm.synthesis_calls[0][1] == "Paragraph one.\n\nParagraph two."
            assert search.calls == ["example query"]

    asyncio.run(runner())


def test_ui_more_info_uses_persisted_value_without_new_lookup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    app.storage.update_more_info(article_content.article_id, "Saved background")
    app.load_articles()
    llm = FakeMoreInfoLLM(responses=["Fresh background"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                if more_info_screen(app) is not None and more_info_body(app) == "Saved background":
                    break

            assert more_info_body(app) == "Saved background"
            assert llm.query_calls == []
            assert search.calls == []

    asyncio.run(runner())


def test_ui_more_info_refresh_persists_new_value(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    app.storage.update_more_info(article_content.article_id, "Saved background")
    app.load_articles()
    app.llm_client = FakeMoreInfoLLM(responses=["Fresh background"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                if more_info_body(app) == "Saved background":
                    break

            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                if more_info_body(app) == "Fresh background":
                    break

            assert more_info_body(app) == "Fresh background"

    asyncio.run(runner())

    reloaded = NewsReaderApp(app_config, storage_path)
    try:
        reloaded.load_articles()
        assert reloaded.current_article is not None
        assert reloaded.current_article.more_info == "Fresh background"
    finally:
        reloaded.storage.close()


def test_ui_navigation_closes_more_info_and_cancels_lookup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    newer_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Newer title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Newer source text",
    )
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")

    llm = BlockingQueryLLM()
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = FakeSearchClient([])  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                if llm.started.is_set():
                    break

            assert llm.started.is_set()
            assert more_info_screen(app) is not None

            await pilot.press("right")
            for _ in range(20):
                await pilot.pause()
                if llm.cancelled.is_set():
                    break

            assert llm.cancelled.is_set()
            assert more_info_screen(app) is None
            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id
            assert body_source(app) == "Newer text"

    asyncio.run(runner())


def test_ui_more_info_shows_loading_indicator_while_waiting_for_llm(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = BlockingQueryLLM()
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = FakeSearchClient([])  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("m")
            for _ in range(20):
                await pilot.pause()
                if llm.started.is_set() and more_info_screen(app) is not None:
                    break

            screen = more_info_screen(app)
            assert llm.started.is_set()
            assert screen is not None
            assert "State: asking configured llm for search query..." in screen.query_one(
                "#more-info-header", Static
            ).content
            assert more_info_loading_indicator(app).display is True

            await pilot.press("escape")
            for _ in range(20):
                await pilot.pause()
                if llm.cancelled.is_set():
                    break

            assert llm.cancelled.is_set()

    asyncio.run(runner())
