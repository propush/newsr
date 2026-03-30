from __future__ import annotations

import asyncio
import webbrowser
from datetime import UTC, datetime
from threading import Event
from unittest.mock import patch

from rich.cells import cell_len
from textual.color import Color
from textual.widgets import DataTable
from textual.widgets import Footer, Input, ListView, LoadingIndicator, Markdown, Static

from newsr.export import ExportAction, ExportResult
from newsr.cancellation import RefreshCancellation
import pytest

from newsr.domain import AppOptions, ArticleContent, ProviderTarget, ViewMode
from newsr.providers.search import SearchResult
from newsr.ui import (
    ArticleQuestionScreen,
    CategorySelectionScreen,
    ExportScreen,
    OLD_FIDO_THEME,
    MoreInfoScreen,
    NewsReaderApp,
    OpenLinkConfirmScreen,
    QuickNavScreen,
)


def body_source(app: NewsReaderApp) -> str:
    return app.query_one("#article-body", Markdown).source


def url_source(app: NewsReaderApp) -> str:
    return app.query_one("#article-url", Static).content


def more_info_screen(app: NewsReaderApp) -> MoreInfoScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, MoreInfoScreen):
            return screen
    return None


def more_info_body(app: NewsReaderApp) -> str:
    screen = more_info_screen(app)
    assert screen is not None
    return screen.query_one("#more-info-body", Markdown).source


def more_info_pane(app: NewsReaderApp):
    screen = more_info_screen(app)
    assert screen is not None
    return screen.query_one("#more-info-pane")


def more_info_loading_indicator(app: NewsReaderApp) -> LoadingIndicator:
    screen = more_info_screen(app)
    assert screen is not None
    return screen.query_one("#more-info-loading", LoadingIndicator)


def article_qa_screen(app: NewsReaderApp) -> ArticleQuestionScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, ArticleQuestionScreen):
            return screen
    return None


def article_qa_body(app: NewsReaderApp) -> str:
    screen = article_qa_screen(app)
    assert screen is not None
    return screen.query_one("#article-qa-body", Markdown).source


def article_qa_input(app: NewsReaderApp) -> Input:
    screen = article_qa_screen(app)
    assert screen is not None
    return screen.query_one("#article-qa-input", Input)


def article_qa_loading_indicator(app: NewsReaderApp) -> LoadingIndicator:
    screen = article_qa_screen(app)
    assert screen is not None
    return screen.query_one("#article-qa-loading", LoadingIndicator)


def article_qa_source_list(app: NewsReaderApp) -> ListView:
    screen = article_qa_screen(app)
    assert screen is not None
    return screen.query_one("#article-qa-source-list", ListView)


def open_link_confirm_screen(app: NewsReaderApp) -> OpenLinkConfirmScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, OpenLinkConfirmScreen):
            return screen
    return None


def export_screen(app: NewsReaderApp) -> ExportScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, ExportScreen):
            return screen
    return None


def status_loading_indicator(app: NewsReaderApp) -> LoadingIndicator:
    return app.query_one("#status-indicator", LoadingIndicator)


def quick_nav_screen(app: NewsReaderApp) -> QuickNavScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, QuickNavScreen):
            return screen
    return None


def quick_nav_table(app: NewsReaderApp) -> DataTable:
    screen = quick_nav_screen(app)
    assert screen is not None
    return screen.query_one("#quick-nav-table", DataTable)


def quick_nav_rows(app: NewsReaderApp) -> list[list[str]]:
    table = quick_nav_table(app)
    rows: list[list[str]] = []
    for row_index in range(table.row_count):
        row = table.get_row_at(row_index)
        rows.append([str(cell) for cell in row])
    return rows


def quick_nav_selection_text(app: NewsReaderApp) -> str:
    screen = quick_nav_screen(app)
    assert screen is not None
    return str(screen.query_one("#quick-nav-selection", Static).content)


def category_screen(app: NewsReaderApp) -> CategorySelectionScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, CategorySelectionScreen):
            return screen
    return None


def provider_list(app: NewsReaderApp) -> DataTable:
    screen = category_screen(app)
    assert screen is not None
    return screen.query_one("#provider-list", DataTable)


def provider_rows(app: NewsReaderApp) -> list[list[str]]:
    table = provider_list(app)
    rows: list[list[str]] = []
    for row_index in range(table.row_count):
        row = table.get_row_at(row_index)
        rows.append([str(cell) for cell in row])
    return rows


def provider_row_index(app: NewsReaderApp, display_name: str) -> int:
    for row_index, row in enumerate(provider_rows(app)):
        if len(row) > 1 and row[1] == display_name:
            return row_index
    raise AssertionError(f"provider row not found for {display_name}")


def target_list(app: NewsReaderApp) -> DataTable:
    screen = category_screen(app)
    assert screen is not None
    return screen.query_one("#target-list", DataTable)


def target_rows(app: NewsReaderApp) -> list[list[str]]:
    table = target_list(app)
    rows: list[list[str]] = []
    for row_index in range(table.row_count):
        row = table.get_row_at(row_index)
        rows.append([str(cell) for cell in row])
    return rows


def source_status_text(app: NewsReaderApp) -> str:
    screen = category_screen(app)
    assert screen is not None
    return str(screen.query_one("#source-status", Static).content)


def provider_home_screen(app: NewsReaderApp):
    return app if app.provider_home_open else None


def provider_home_table(app: NewsReaderApp) -> DataTable:
    assert app.provider_home_open
    return app.query_one("#provider-home-table", DataTable)


def provider_home_rows(app: NewsReaderApp) -> list[list[str]]:
    table = provider_home_table(app)
    rows: list[list[str]] = []
    for row_index in range(table.row_count):
        row = table.get_row_at(row_index)
        rows.append([str(cell).strip() for cell in row])
    return rows


def provider_home_row_index(app: NewsReaderApp, display_name: str) -> int:
    for row_index, row in enumerate(provider_home_rows(app)):
        if row[0] == display_name:
            return row_index
    raise AssertionError(f"provider home row not found for {display_name}")


def provider_home_footer_text(app: NewsReaderApp) -> str:
    return str(app.query_one("#article-url", Static).content)


def footer_bindings(app: NewsReaderApp) -> list[tuple[str, str, str]]:
    footer = app.query_one(Footer)
    return [(child.key_display, child.description, child.action) for child in footer.children]


class FakeMoreInfoLLM:
    def __init__(self, *, query: str = "example query", responses: list[str] | None = None) -> None:
        self.query = query
        self.responses = responses or ["More info result"]
        self.query_calls: list[tuple[str, str]] = []
        self.synthesis_calls: list[tuple[str, str, list[SearchResult]]] = []

    def build_search_query(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.query_calls.append((article_title, article_text))
        return self.query

    def synthesize_more_info(
        self,
        article_title: str,
        article_text: str,
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.synthesis_calls.append((article_title, article_text, search_results))
        index = min(len(self.synthesis_calls) - 1, len(self.responses) - 1)
        return self.responses[index]


class FakeSearchClient:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.calls: list[str] = []

    def search(
        self, query: str, limit: int = 5, cancellation: RefreshCancellation | None = None
    ) -> list[SearchResult]:
        self.calls.append(query)
        return self.results[:limit]


class BlockingQueryLLM:
    def __init__(self) -> None:
        self.started = Event()
        self.cancelled = Event()

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


class FakeArticleQALLM:
    def __init__(self, *, query: str = "latest context", answers: list[str] | None = None) -> None:
        self.query = query
        self.answers = answers or ["Article answer"]
        self.query_calls: list[tuple[str, str, str, str, list[tuple[str, str]]]] = []
        self.answer_calls: list[tuple[str, str, str, str, list[tuple[str, str]], list[SearchResult]]] = []

    def build_article_question_query(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.query_calls.append((article_title, article_text, question, current_datetime, list(chat_history)))
        return self.query

    def answer_article_question(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.answer_calls.append(
            (article_title, article_text, question, current_datetime, list(chat_history), list(search_results))
        )
        index = min(len(self.answer_calls) - 1, len(self.answers) - 1)
        return self.answers[index]


class FlakyArticleQALLM(FakeArticleQALLM):
    def __init__(self, *, answer_failures: set[int], answers: list[str] | None = None) -> None:
        super().__init__(answers=answers)
        self.answer_failures = answer_failures

    def answer_article_question(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        answer_call_number = len(self.answer_calls) + 1
        if answer_call_number in self.answer_failures:
            self.answer_calls.append(
                (article_title, article_text, question, current_datetime, list(chat_history), list(search_results))
            )
            raise RuntimeError(f"synthetic failure {answer_call_number}")
        return super().answer_article_question(
            article_title,
            article_text,
            question,
            current_datetime,
            chat_history,
            search_results,
            cancellation,
        )


class BlockingArticleQALLM:
    def __init__(self) -> None:
        self.started = Event()
        self.cancelled = Event()

    def build_article_question_query(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        assert cancellation is not None
        self.started.set()
        cancellation.cancelled_event.wait(timeout=5)
        if cancellation.is_cancelled:
            self.cancelled.set()
        cancellation.raise_if_cancelled()
        return "unused"

    def answer_article_question(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        raise AssertionError("answer_article_question should not run after cancellation")


class FakeSourceProvider:
    provider_id = "bbc"
    display_name = "BBC News"

    def __init__(self, targets: list[ProviderTarget]) -> None:
        self.targets = targets
        self.calls = 0

    def default_targets(self) -> list[ProviderTarget]:
        return list(self.targets)

    def discover_targets(self, cancellation=None) -> list[ProviderTarget]:  # type: ignore[no-untyped-def]
        self.calls += 1
        return list(self.targets)


class BusyStatusPipeline:
    def __init__(self, status_message: str = "summarizing world-1, done 0 of 1") -> None:
        self.started = Event()
        self.release_refresh = Event()
        self.status_message = status_message

    def refresh(self, on_status, on_article_ready, cancellation=None) -> None:  # type: ignore[no-untyped-def]
        on_status(self.status_message)
        self.started.set()
        self.release_refresh.wait(timeout=5)
        on_status("ready")


class FakeExportService:
    def __init__(self, result: ExportResult | None = None) -> None:
        self.result = result or ExportResult(True, "saved png export to exports/test.png")
        self.calls: list[tuple[ExportAction, str, ViewMode, str]] = []

    def export(self, action, *, article, view_mode, theme, config):  # type: ignore[no-untyped-def]
        self.calls.append((action, article.article_id, view_mode, theme.name))
        return self.result


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


def seed_provider_article(
    app: NewsReaderApp,
    *,
    provider_id: str,
    provider_article_id: str,
    title: str,
    body: str,
    minute: int,
    translated_title: str | None = None,
) -> str:
    article_id = f"{provider_id}:{provider_article_id}"
    article = ArticleContent(
        article_id=article_id,
        provider_id=provider_id,
        provider_article_id=provider_article_id,
        url=f"https://example.com/{provider_id}/{provider_article_id}",
        category="world",
        title=title,
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, minute, tzinfo=UTC),
        body=body,
    )
    app.storage.upsert_article_source(article)
    app.storage.update_translation(article_id, translated_title or title, body, "done")
    app.storage.update_summary(article_id, f"Summary for {title}", "done")
    return article_id


def disable_startup_refresh(app: NewsReaderApp) -> None:
    app._start_refresh = lambda: None  # type: ignore[method-assign]


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
            header = header_widget.content
            body = body_source(app)
            assert "Article # 1 of 1" in header
            assert f"Date : {expected_date}" in header
            assert "From : Reporter" not in header
            assert "Title: Translated title" in header
            assert "Area :" not in header
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
            header = app.query_one("#article-header", Static).content
            assert len(app.articles) == 1
            assert app.current_article is not None
            assert app.current_article.article_id == translated.article_id
            assert "Article # 1 of 1" in header
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
            header = header_widget.content
            assert f"Date : {expected_date}" in header
            assert "From : bbc" not in header
            assert "BBC News " in header_widget.border_title
            assert "world" in header_widget.border_title
            assert "From :" not in header_widget.border_title
            assert "Area :" not in header

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
            header = header_widget.content
            assert "From :" not in header
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
            header = app.query_one("#article-header").content
            assert f"Date : {expected_date}" in header
            assert "Date : unknown" not in header

    asyncio.run(runner())


def test_ui_ignores_summary_toggle_without_summary(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, None, "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("s")
            assert app.reader_state.view_mode == ViewMode.FULL

    asyncio.run(runner())


def test_ui_arrow_scroll_actions_do_not_raise(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(80))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", tall_body, "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("down", "up")
            assert app.query_one("#article-pane").scroll_target_y >= 0

    asyncio.run(runner())


def test_ui_space_pagedown_and_b_pageup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(200))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", tall_body, "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            pane = app.query_one("#article-pane")
            assert pane.scroll_target_y == 0

            await pilot.press("space")
            await pilot.pause()
            after_page_down = pane.scroll_target_y
            assert after_page_down > 0

            await pilot.press("b")
            await pilot.pause()
            assert pane.scroll_target_y < after_page_down

    asyncio.run(runner())


def test_ui_space_advances_to_next_article_at_bottom(app_config, tmp_path, article_content) -> None:
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
    tall_body = "\n\n".join(f"Paragraph {index}" for index in range(200))
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Older translated title", tall_body, "done")
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            pane = app.query_one("#article-pane")
            pane.scroll_target_y = pane.max_scroll_y
            await pilot.press("space")
            await pilot.pause()

            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id
            assert body_source(app) == "Newer text"

    asyncio.run(runner())


def test_ui_hides_space_hints_from_footer(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    bindings = {binding.key: binding for _key, binding in app._bindings}

    assert bindings["space"].show is False
    assert bindings["b"].show is False


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


def test_ui_ignores_download_while_refresh_is_running(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._run_refresh)
        return object()

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]
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
        calls.append(app._run_refresh)
        return object()

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

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
        calls.append(app._run_refresh)
        return object()

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

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
        calls.append(app._run_refresh)
        return object()

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

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


def test_ui_rearms_auto_fetch_after_article_list_grows(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    seed_translated_articles(app, 10)

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._run_refresh)
        return object()

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

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
            assert len(calls) == 2

    asyncio.run(runner())


class BlockingReadyPipeline:
    def __init__(self, app: NewsReaderApp, article: ArticleContent) -> None:
        self.app = app
        self.article = article
        self.ready_emitted = Event()
        self.summary_emitted = Event()
        self.release_refresh = Event()

    def refresh(self, on_status, on_article_ready, cancellation=None) -> None:  # type: ignore[no-untyped-def]
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
            header = app.query_one("#article-header").content
            assert "Title: Example title" in header

    asyncio.run(runner())


def test_ui_summary_toggle_keeps_header_and_swaps_body(app_config, tmp_path, article_content) -> None:
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
            header_before = app.query_one("#article-header").content
            body_before = body_source(app)
            url_before = url_source(app)
            await pilot.press("s")
            header_after = app.query_one("#article-header").content
            body_after = body_source(app)
            url_after = url_source(app)
            assert "Title: Translated title" in header_before
            assert "Title: Translated title" in header_after
            assert "Mode : full" in header_before
            assert "Mode : summary" in header_after
            assert body_before == "Translated text"
            assert body_after == "Summary text"
            assert url_before == f"URL: {article_content.url}"
            assert url_after == f"URL: {article_content.url}"

    asyncio.run(runner())


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


def test_ui_opens_article_qa_overlay_and_escape_restores_summary_mode(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            assert body_source(app) == "Summary text"

            await pilot.press("?")
            await pilot.pause()

            screen = article_qa_screen(app)
            assert screen is not None
            assert "State: ready" in screen.query_one("#article-qa-header", Static).content
            assert "Nothing in this chat is saved" in article_qa_body(app)

            await pilot.press("escape")
            await pilot.pause()

            assert article_qa_screen(app) is None
            assert app.reader_state.view_mode == ViewMode.SUMMARY
            assert body_source(app) == "Summary text"

    asyncio.run(runner())


def test_ui_article_qa_submits_question_shows_answer_and_sources(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeArticleQALLM(answers=["Direct answer"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "What happened?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if "Direct answer" in article_qa_body(app):
                    break

            body = article_qa_body(app)
            assert "Question 1" in body
            assert "**You:** What happened?" in body
            assert "### Answer" in body
            assert "Direct answer" in body
            assert "### Sources" in body
            assert "[Context](https://example.com/context)" in body
            assert search.calls == ["latest context"]
            assert llm.query_calls == [
                (
                    "Example title",
                    "Paragraph one.\n\nParagraph two.",
                    "What happened?",
                    llm.query_calls[0][3],
                    [],
                )
            ]
            assert llm.answer_calls[0][0] == "Example title"
            assert llm.answer_calls[0][1] == "Paragraph one.\n\nParagraph two."
            assert llm.answer_calls[0][2] == "What happened?"
            assert llm.answer_calls[0][4] == []
            assert llm.answer_calls[0][5] == [
                SearchResult(title="Context", url="https://example.com/context", snippet="Details")
            ]
            assert llm.answer_calls[0][3]

    asyncio.run(runner())


def test_ui_article_qa_source_list_opens_browser_with_keyboard(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.llm_client = FakeArticleQALLM(answers=["Direct answer"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    opened_urls: list[tuple[str, int]] = []
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0: opened_urls.append((url, new)) or True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "What happened?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if "Direct answer" in article_qa_body(app):
                    break

            assert article_qa_input(app).has_focus
            await pilot.press("tab")
            await pilot.pause()
            assert article_qa_source_list(app).has_focus
            await pilot.press("enter")
            await pilot.pause()
            confirm = open_link_confirm_screen(app)
            assert confirm is not None
            assert "URL: https://example.com/context" in confirm.query_one("#open-link-body", Static).content
            assert opened_urls == []
            await pilot.press("enter")
            await pilot.pause()

    asyncio.run(runner())

    assert opened_urls == [("https://example.com/context", 2)]


def test_ui_article_qa_markdown_link_click_opens_browser(
    app_config, tmp_path, article_content, monkeypatch
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.llm_client = FakeArticleQALLM(answers=["Direct answer"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    opened_urls: list[tuple[str, int]] = []
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0: opened_urls.append((url, new)) or True)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "What happened?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if "Direct answer" in article_qa_body(app):
                    break

            screen = article_qa_screen(app)
            assert screen is not None
            markdown = screen.query_one("#article-qa-body", Markdown)
            screen.on_markdown_link_clicked(
                Markdown.LinkClicked(markdown, "https://example.com/новости/игры?тема=БАФТА")
            )
            await pilot.pause()
            confirm = open_link_confirm_screen(app)
            assert confirm is not None
            assert (
                "URL: https://example.com/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8/"
                "%D0%B8%D0%B3%D1%80%D1%8B?%D1%82%D0%B5%D0%BC%D0%B0=%D0%91%D0%90%D0%A4%D0%A2%D0%90"
            ) in confirm.query_one("#open-link-body", Static).content
            assert opened_urls == []
            await pilot.press("enter")
            await pilot.pause()

    asyncio.run(runner())

    assert opened_urls == [
        (
            "https://example.com/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8/"
            "%D0%B8%D0%B3%D1%80%D1%8B?%D1%82%D0%B5%D0%BC%D0%B0=%D0%91%D0%90%D0%A4%D0%A2%D0%90",
            2,
        )
    ]


def test_ui_article_qa_follow_up_uses_prior_turns(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeArticleQALLM(answers=["Answer 1", "Answer 2"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()

            article_qa_input(app).value = "First question?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer 1" in article_qa_body(app):
                    break

            article_qa_input(app).value = "And now?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer 2" in article_qa_body(app):
                    break

            body = article_qa_body(app)
            assert "First question?" in body
            assert "Answer 1" in body
            assert "And now?" in body
            assert "Answer 2" in body
            assert llm.query_calls[1][4] == [("First question?", "Answer 1")]
            assert llm.answer_calls[1][4] == [("First question?", "Answer 1")]

    asyncio.run(runner())


def test_ui_article_qa_third_turn_uses_full_answered_history(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FakeArticleQALLM(answers=["Answer 1", "Answer 2", "Answer 3"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()

            for question, expected_answer in [
                ("First question?", "Answer 1"),
                ("Second question?", "Answer 2"),
                ("Third question?", "Answer 3"),
            ]:
                article_qa_input(app).value = question
                await pilot.press("enter")
                for _ in range(20):
                    await pilot.pause()
                    if expected_answer in article_qa_body(app):
                        break

            assert llm.query_calls[2][4] == [
                ("First question?", "Answer 1"),
                ("Second question?", "Answer 2"),
            ]
            assert llm.answer_calls[2][4] == [
                ("First question?", "Answer 1"),
                ("Second question?", "Answer 2"),
            ]

    asyncio.run(runner())


def test_ui_article_qa_failed_turn_is_excluded_from_follow_up_history(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = FlakyArticleQALLM(answer_failures={2}, answers=["Answer 1", "Answer 3"])
    search = FakeSearchClient(
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = search  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()

            article_qa_input(app).value = "First question?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer 1" in article_qa_body(app):
                    break

            article_qa_input(app).value = "This one fails?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer unavailable" in article_qa_body(app):
                    break

            article_qa_input(app).value = "What about now?"
            await pilot.press("enter")
            for _ in range(20):
                await pilot.pause()
                if "Answer 3" in article_qa_body(app):
                    break

            assert llm.query_calls[2][4] == [("First question?", "Answer 1")]
            assert llm.answer_calls[2][4] == [("First question?", "Answer 1")]

    asyncio.run(runner())


def test_ui_article_qa_escape_cancels_inflight_request_and_clears_session(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    llm = BlockingArticleQALLM()
    app.llm_client = llm  # type: ignore[assignment]
    app.search_client = FakeSearchClient([])  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "Need current context?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if llm.started.is_set() and article_qa_screen(app) is not None:
                    break

            screen = article_qa_screen(app)
            assert llm.started.is_set()
            assert screen is not None
            assert "State: asking configured llm for web search query..." in screen.query_one(
                "#article-qa-header", Static
            ).content
            assert article_qa_loading_indicator(app).display is True

            await pilot.press("escape")
            for _ in range(20):
                await pilot.pause()
                if llm.cancelled.is_set():
                    break

            assert llm.cancelled.is_set()
            assert article_qa_screen(app) is None

            await pilot.press("?")
            await pilot.pause()
            assert "Need current context?" not in article_qa_body(app)
            assert "Nothing in this chat is saved" in article_qa_body(app)

    asyncio.run(runner())


def test_ui_article_qa_does_not_persist_answers(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Translated title", "Translated text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    app.llm_client = FakeArticleQALLM(answers=["Direct answer"])  # type: ignore[assignment]
    app.search_client = FakeSearchClient(  # type: ignore[assignment]
        [SearchResult(title="Context", url="https://example.com/context", snippet="Details")]
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("?")
            await pilot.pause()
            article_qa_input(app).value = "What changed?"
            await pilot.press("enter")

            for _ in range(20):
                await pilot.pause()
                if "Direct answer" in article_qa_body(app):
                    break

            await pilot.press("escape")
            await pilot.pause()

    asyncio.run(runner())

    reloaded = NewsReaderApp(app_config, storage_path)
    try:
        reloaded.load_articles()
        assert reloaded.current_article is not None
        assert reloaded.current_article.more_info is None
    finally:
        reloaded.storage.close()


def test_ui_help_lists_article_qa_shortcut(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("h")
            await pilot.pause()
            help_text = app.screen.query_one("#help-text", Static).content
            assert "?: ask about article" in help_text

    asyncio.run(runner())


def test_ui_loads_articles_in_insertion_order_and_shows_position(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    appended_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Appended title",
        author="Reporter",
        published_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        body="Appended source text",
    )
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Older summary", "done")
    app.storage.upsert_article_source(appended_article)
    app.storage.update_translation(appended_article.article_id, "Appended translated title", "Appended text", "done")
    app.storage.update_summary(appended_article.article_id, "Appended summary", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id
            header = app.query_one("#article-header").content
            body = body_source(app)
            assert "Article # 1 of 2" in header
            assert "Title: Older translated title" in header
            assert "Older text" in body
            assert url_source(app) == f"URL: {article_content.url}"

            await pilot.press("right")

            header = app.query_one("#article-header").content
            body = body_source(app)
            assert app.current_article is not None
            assert app.current_article.article_id == appended_article.article_id
            assert "Article # 2 of 2" in header
            assert "Title: Appended translated title" in header
            assert "Appended text" in body
            assert url_source(app) == f"URL: {appended_article.url}"

    asyncio.run(runner())


def test_ui_quick_nav_preserves_order_and_filters_missing_titles(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    hidden_article = ArticleContent(
        article_id="test-0",
        provider_id="bbc",
        provider_article_id="test-0",
        url="https://www.bbc.com/news/test-0",
        category="business",
        title="Hidden title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 3, tzinfo=UTC),
        body="Hidden source text",
    )
    appended_article = ArticleContent(
        article_id="test-2",
        provider_id="bbc",
        provider_article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Appended title",
        author="Reporter",
        published_at=datetime(2026, 3, 20, 12, 5, tzinfo=UTC),
        body="Appended source text",
    )
    app.storage.upsert_article_source(hidden_article)
    app.storage.update_translation(hidden_article.article_id, None, "Hidden text", "done")
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.upsert_article_source(appended_article)
    app.storage.update_translation(appended_article.article_id, "Appended translated title", "Appended text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            screen = quick_nav_screen(app)
            assert screen is not None

            table = quick_nav_table(app)
            rows = quick_nav_rows(app)
            assert table.row_count == 2
            assert rows == [
                ["", "2026-03-25", "Older translated title", "BBC News", "world"],
                ["", "2026-03-20", "Appended translated title", "BBC News", "technology"],
            ]
            assert table.cursor_row == 0
            assert quick_nav_selection_text(app) == "Selected 1 of 2"

    asyncio.run(runner())


def test_ui_quick_nav_enter_opens_selected_article_and_escape_closes_without_changing_selection(
    app_config, tmp_path, article_content
) -> None:
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

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id

            await pilot.press("l", "down", "enter")
            await pilot.pause()

            assert quick_nav_screen(app) is None
            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id
            assert body_source(app) == "Newer text"

            await pilot.press("l", "escape")
            await pilot.pause()

            assert quick_nav_screen(app) is None
            assert app.current_article is not None
            assert app.current_article.article_id == newer_article.article_id

    asyncio.run(runner())


def test_ui_quick_nav_updates_selected_counter_when_cursor_moves(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    for index in range(3):
        article = ArticleContent(
            article_id=f"test-{index + 1}",
            url=f"https://www.bbc.com/news/test-{index + 1}",
            category="world" if index == 0 else "technology",
            title=f"Title {index + 1}",
            author="Reporter",
            published_at=datetime(2026, 3, 25, 12, index, tzinfo=UTC),
            body=f"Source text {index + 1}",
        )
        app.storage.upsert_article_source(article)
        app.storage.update_translation(article.article_id, f"Translated title {index + 1}", "Text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            assert quick_nav_selection_text(app) == "Selected 1 of 3"

            await pilot.press("down", "down")
            await pilot.pause()

            assert quick_nav_selection_text(app) == "Selected 3 of 3"

    asyncio.run(runner())


def test_ui_quick_nav_falls_back_to_first_visible_row_when_current_article_is_filtered_out(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    current_hidden_article = ArticleContent(
        article_id="test-1",
        provider_id="bbc",
        provider_article_id="test-1",
        url="https://www.bbc.com/news/test-1",
        category="world",
        title="Hidden current title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Hidden current source text",
    )
    visible_article = ArticleContent(
        article_id="test-2",
        provider_id="bbc",
        provider_article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Visible title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Visible source text",
    )
    app.storage.upsert_article_source(current_hidden_article)
    app.storage.update_translation(current_hidden_article.article_id, None, "Hidden text", "done")
    app.storage.upsert_article_source(visible_article)
    app.storage.update_translation(visible_article.article_id, "Visible translated title", "Visible text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == current_hidden_article.article_id

            await pilot.press("l")
            await pilot.pause()

            table = quick_nav_table(app)
            rows = quick_nav_rows(app)
            assert table.row_count == 1
            assert table.cursor_row == 0
            assert rows == [["", "2026-03-25", "Visible translated title", "BBC News", "technology"]]
            assert quick_nav_selection_text(app) == "Selected 1 of 1"

    asyncio.run(runner())


def test_ui_quick_nav_trims_long_titles_to_available_width(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    long_title = "Translated title " + ("x" * 80)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, long_title, "Translated text", "done")

    async def runner() -> None:
        async with app.run_test(size=(50, 20)) as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            rows = quick_nav_rows(app)
            assert len(rows) == 1
            assert rows[0][2].endswith("...")
            assert len(rows[0][2]) <= 12

    asyncio.run(runner())


def test_ui_quick_nav_falls_back_to_provider_id_when_display_name_is_unknown(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    article = ArticleContent(
        article_id="unknown:test-1",
        provider_id="unknown",
        provider_article_id="test-1",
        url="https://example.com/test-1",
        category="alerts",
        title="Unknown provider title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Unknown provider source text",
    )
    app.storage.upsert_article_source(article)
    app.storage.update_translation(article.article_id, "Unknown translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            rows = quick_nav_rows(app)
            assert rows == [[">", "2026-03-25", "Unknown translated title", "unknown", "alerts"]]

    asyncio.run(runner())


def test_ui_quick_nav_shows_empty_state_when_no_translated_titles_are_available(
    app_config, tmp_path, article_content
) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, None, "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            screen = quick_nav_screen(app)
            assert screen is not None
            table = quick_nav_table(app)
            empty = screen.query_one("#quick-nav-empty", Static)
            assert table.display is False
            assert empty.display is True
            assert empty.content == "No translated articles available."
            assert quick_nav_selection_text(app) == "Selected 0 of 0"

    asyncio.run(runner())


def test_ui_quick_nav_table_shows_visible_scrollbar_styles(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    for index in range(20):
        article = ArticleContent(
            article_id=f"test-{index + 1}",
            url=f"https://www.bbc.com/news/test-{index + 1}",
            category="world",
            title=f"Title {index + 1}",
            author="Reporter",
            published_at=datetime(2026, 3, 25, 12, index, tzinfo=UTC),
            body=f"Source text {index + 1}",
        )
        app.storage.upsert_article_source(article)
        app.storage.update_translation(article.article_id, f"Translated title {index + 1}", "Text", "done")

    async def runner() -> None:
        async with app.run_test(size=(50, 12)) as pilot:
            await pilot.pause()
            await pilot.press("l")
            await pilot.pause()

            table = quick_nav_table(app)
            styles = table.styles
            assert styles.scrollbar_visibility == "visible"
            assert styles.scrollbar_gutter == "stable"

    asyncio.run(runner())


def test_ui_restores_last_read_article_on_restart(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    appended_article = ArticleContent(
        article_id="test-2",
        url="https://www.bbc.com/news/test-2",
        category="technology",
        title="Appended title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 5, tzinfo=UTC),
        body="Appended source text",
    )
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Older summary", "done")
    app.storage.upsert_article_source(appended_article)
    app.storage.update_translation(
        appended_article.article_id, "Appended translated title", "Appended text", "done"
    )
    app.storage.update_summary(appended_article.article_id, "Appended summary", "done")

    async def first_run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("right")
            assert app.current_article is not None
            assert app.current_article.article_id == appended_article.article_id

    asyncio.run(first_run())

    restarted = NewsReaderApp(app_config, storage_path)

    async def second_run() -> None:
        async with restarted.run_test() as pilot:
            await pilot.pause()
            assert restarted.current_article is not None
            assert restarted.current_article.article_id == appended_article.article_id
            header = restarted.query_one("#article-header").content
            assert "Article # 2 of 2" in header

    asyncio.run(second_run())


def test_ui_falls_back_when_last_read_article_is_missing(app_config, tmp_path, article_content) -> None:
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
    app.storage.update_summary(article_content.article_id, "Older summary", "done")
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")
    app.storage.update_summary(newer_article.article_id, "Newer summary", "done")
    app.storage.save_reader_state(
        "[ALL]",
        app.reader_state.__class__(
            article_id=newer_article.article_id,
            view_mode=ViewMode.FULL,
            scroll_offset=7,
        )
    )
    app.storage.connection.execute("DELETE FROM articles WHERE article_id = ?", (newer_article.article_id,))
    app.storage.connection.execute("DELETE FROM jobs WHERE article_id = ?", (newer_article.article_id,))
    app.storage.connection.commit()
    app.storage.close()

    restarted = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with restarted.run_test() as pilot:
            await pilot.pause()
            assert restarted.current_article is not None
            assert restarted.current_article.article_id == article_content.article_id
            assert restarted.reader_state.article_id == article_content.article_id
            header = restarted.query_one("#article-header").content
            assert "Article # 1 of 1" in header

    asyncio.run(runner())


def test_ui_restores_last_read_article_on_restart_with_saved_theme(
    app_config, tmp_path, article_content
) -> None:
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
    app.storage.upsert_article_source(newer_article)
    app.storage.update_translation(newer_article.article_id, "Newer translated title", "Newer text", "done")
    app.storage.update_summary(newer_article.article_id, "Newer summary", "done")
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(
        article_content.article_id, "Older translated title", "Older text", "done"
    )
    app.storage.update_summary(article_content.article_id, "Older summary", "done")
    app.storage.save_reader_state(
        "[ALL]",
        app.reader_state.__class__(
            article_id=newer_article.article_id,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        )
    )
    app.storage.save_options(AppOptions(theme_name="old fido"))
    app.storage.close()

    restarted = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with restarted.run_test() as pilot:
            await pilot.pause()
            assert restarted.theme == "old fido"
            assert restarted.current_article is not None
            assert restarted.current_article.article_id == newer_article.article_id
            state = restarted.storage.load_reader_state("[ALL]")
            assert state.article_id == newer_article.article_id

    asyncio.run(runner())


class CancellablePipeline:
    def __init__(self) -> None:
        self.started = Event()
        self.cancelled = Event()

    def refresh(self, on_status, on_article_ready, cancellation=None) -> None:  # type: ignore[no-untyped-def]
        self.started.set()
        assert cancellation is not None
        cancellation.cancelled_event.wait(timeout=5)
        self.cancelled.set()


class SlowShutdownPipeline:
    def __init__(self) -> None:
        self.started = Event()
        self.cancelled = Event()
        self.release_refresh = Event()

    def refresh(self, on_status, on_article_ready, cancellation=None) -> None:  # type: ignore[no-untyped-def]
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


def test_ui_pressing_q_exits_without_waiting_for_refresh_shutdown(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    pipeline = SlowShutdownPipeline()
    app.pipeline = pipeline  # type: ignore[assignment]

    async def runner() -> None:
        async with app.run_test() as pilot:
            for _ in range(20):
                await pilot.pause()
                if pipeline.started.is_set():
                    break
            assert pipeline.started.is_set()
            quit_task = asyncio.create_task(pilot.press("q"))
            for _ in range(20):
                await pilot.pause()
                if quit_task.done():
                    break
            assert pipeline.cancelled.is_set()
            assert quit_task.done()
            pipeline.release_refresh.set()

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


def test_ui_pressing_o_opens_current_article_in_browser(
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
            assert opened_urls == [(article_content.url, 2)]
            assert app.query_one("#status", Static).content == "opened article in browser"

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

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]
    monkeypatch.setattr(webbrowser, "open", fake_open)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("o")
            assert calls == []
            assert app.query_one("#status", Static).content == "ready"
            assert url_source(app) == ""

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


def test_ui_pressing_e_without_current_article_sets_status(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is None
            assert app.query_one("#status", Static).content == "no article to export"

    asyncio.run(runner())


def test_ui_pressing_e_opens_export_screen(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            screen = export_screen(app)
            assert screen is not None
            assert "Title: Translated title" in screen.query_one("#export-body", Static).content
            assert "Mode: full" in screen.query_one("#export-body", Static).content

    asyncio.run(runner())


def test_ui_export_screen_runs_action_and_closes_on_success(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    fake_export = FakeExportService()
    app.export_service = fake_export

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("s")
            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is not None

            await pilot.press("2")
            await pilot.pause()

            assert fake_export.calls == [(ExportAction.COPY_PNG, article_content.article_id, ViewMode.SUMMARY, app.theme)]
            assert export_screen(app) is None
            assert app.query_one("#status", Static).content == "saved png export to exports/test.png"

    asyncio.run(runner())


def test_ui_export_screen_arrow_keys_move_focus_and_activate_selection(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.storage.update_summary(article_content.article_id, "Summary text", "done")
    fake_export = FakeExportService()
    app.export_service = fake_export

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is not None
            assert getattr(app.focused, "id", None) == "export-save-png"

            await pilot.press("right")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "export-copy-png"

            await pilot.press("down")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "export-copy-markdown"

            await pilot.press("down")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "export-cancel"

            await pilot.press("up")
            await pilot.pause()
            assert getattr(app.focused, "id", None) == "export-copy-markdown"

            await pilot.press("enter")
            await pilot.pause()

            assert fake_export.calls == [(ExportAction.COPY_MARKDOWN, article_content.article_id, ViewMode.FULL, app.theme)]
            assert export_screen(app) is None

    asyncio.run(runner())


def test_ui_export_screen_stays_open_on_failure(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.export_service = FakeExportService(ExportResult(False, "clipboard image export is not supported"))

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is not None

            await pilot.press("2")
            await pilot.pause()

            assert export_screen(app) is not None
            assert app.query_one("#status", Static).content == "clipboard image export is not supported"

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


def test_ui_applies_saved_theme_on_startup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    seeded_app = NewsReaderApp(app_config, storage_path)
    seeded_app.storage.save_reader_state(
        "[ALL]",
        seeded_app.reader_state.__class__(
            article_id=None,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        )
    )
    seeded_app.storage.save_options(AppOptions(theme_name="gruvbox"))
    seeded_app.storage.upsert_article_source(article_content)
    seeded_app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    seeded_app.storage.close()
    app = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.theme == "gruvbox"

    asyncio.run(runner())


def test_ui_persists_theme_changes(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            app.theme = "gruvbox"
            await pilot.pause()
            options = app.storage.load_options()
            assert options.theme_name == "gruvbox"

    asyncio.run(runner())


def test_ui_registers_old_fido_theme(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    theme = app.get_theme("old fido")

    assert theme == OLD_FIDO_THEME
    assert theme.primary == "#d8c24a"
    assert theme.accent == "#c8c8c8"
    assert theme.background == "#000000"


def test_ui_keeps_summary_hotkey_fixed_when_localizing_labels(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    summary_bindings = app._bindings.get_bindings_for_key("s")

    assert len(summary_bindings) == 1
    assert summary_bindings[0].action == "toggle_summary"
    assert summary_bindings[0].description == "Summary"


def test_ui_keeps_summary_hotkey_fixed_in_russian_locale(app_config, tmp_path) -> None:
    app_config.ui.locale = "ru"
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    summary_bindings = app._bindings.get_bindings_for_key("s")

    assert len(summary_bindings) == 1
    assert summary_bindings[0].action == "toggle_summary"
    assert summary_bindings[0].description == "Сводка"


def test_ui_ignores_invalid_saved_theme(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    seeded_app = NewsReaderApp(app_config, storage_path)
    default_theme = seeded_app.theme
    seeded_app.storage.save_reader_state(
        "[ALL]",
        seeded_app.reader_state.__class__(
            article_id=None,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        )
    )
    seeded_app.storage.save_options(AppOptions(theme_name="not-a-theme"))
    seeded_app.storage.upsert_article_source(article_content)
    seeded_app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    seeded_app.storage.close()
    app = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.theme == default_theme

    asyncio.run(runner())


def test_ui_applies_saved_old_fido_theme_on_startup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    seeded_app = NewsReaderApp(app_config, storage_path)
    seeded_app.storage.save_reader_state(
        "[ALL]",
        seeded_app.reader_state.__class__(
            article_id=None,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        )
    )
    seeded_app.storage.save_options(AppOptions(theme_name="old fido"))
    seeded_app.storage.upsert_article_source(article_content)
    seeded_app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    seeded_app.storage.close()
    app = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.theme == "old fido"

    asyncio.run(runner())


def test_ui_source_manager_loads_current_provider_and_targets(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and provider_list(app).row_count and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            provider_statuses = {
                row[1]: row[0]
                for row in provider_rows(app)
            }
            assert provider_statuses["BBC News"] == "[x]"
            assert provider_statuses["TechCrunch"] == "[ ]"
            assert provider_statuses["The Hacker News"] == "[ ]"
            assert provider_statuses["Ars Technica"] == "[ ]"
            assert len(provider_statuses) == len(app.storage.list_providers())

            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()
            assert target_rows(app)[:4] == [
                ["[x]", "World"],
                ["[x]", "Technology"],
                ["[x]", "Business"],
                ["[x]", "Entertainment And Arts"],
            ]
            status_text = source_status_text(app)
            assert f"Loaded {len(app.storage.list_providers())} providers." in status_text
            assert "Enabled 1." in status_text

    asyncio.run(runner())


def test_ui_source_manager_switches_from_long_target_list_to_shorter_one(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and provider_list(app).row_count and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")

            provider_list(app).move_cursor(row=provider_row_index(app, "Ars Technica"), column=0, animate=False)
            await pilot.pause()
            target_list(app).move_cursor(row=6, column=0, animate=False)
            await pilot.pause()

            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()

            assert target_rows(app)[:4] == [
                ["[x]", "World"],
                ["[x]", "Technology"],
                ["[x]", "Business"],
                ["[x]", "Entertainment And Arts"],
            ]

    asyncio.run(runner())


def test_ui_source_manager_refreshes_provider_catalog(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.providers["bbc"] = FakeSourceProvider(
        [
            ProviderTarget(
                provider_id="bbc",
                target_key="science",
                target_kind="category",
                label="Science",
                payload={"slug": "science"},
            ),
            ProviderTarget(
                provider_id="bbc",
                target_key="culture",
                target_kind="category",
                label="Culture",
                payload={"slug": "culture"},
            ),
        ]
    )
    app.storage.replace_provider_targets("bbc", [])
    app.storage.set_selected_targets("bbc", [])

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()
            assert app.providers["bbc"].calls == 1
            assert [row[1] for row in target_rows(app)] == ["Science", "Culture"]

    asyncio.run(runner())


def test_ui_source_manager_save_persists_selection_and_starts_refresh(app_config, tmp_path) -> None:
    launch_calls: list[object] = []
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    original_start_refresh = app._start_refresh
    disable_startup_refresh(app)

    def fake_launch_refresh_thread() -> object:
        launch_calls.append(object())
        return launch_calls[-1]

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            assert screen is not None
            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()
            app._start_refresh = original_start_refresh  # type: ignore[method-assign]
            screen.action_toggle_item()
            screen.action_save_selection()
            await pilot.pause()
            assert category_screen(app) is None
            assert len(launch_calls) == 1
            providers = app.storage.list_providers()
            assert any(provider.provider_id == "bbc" and provider.enabled is False for provider in providers)

    asyncio.run(runner())


def test_ui_source_manager_save_defers_when_refresh_running(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    app.refresh_in_progress = True
    launch_calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        launch_calls.append(object())
        return launch_calls[-1]

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            initial_header = app.query_one("#article-header", Static).content
            initial_body = body_source(app)
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")
            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()
            await pilot.press("tab", "space")
            await pilot.press("a")
            await pilot.pause()
            assert [target.target_key for target in app.storage.list_selected_targets("bbc")] == [
                "technology",
                "business",
                "entertainment_and_arts",
            ]
            assert "next refresh will use updated provider settings" in app.status_text
            assert len(launch_calls) == 0
            assert app.query_one("#article-header", Static).content == initial_header
            assert body_source(app) == initial_body

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_starts_with_all_then_enabled_providers_sorted_by_unread(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-2",
        title="TC 2",
        body="TC body 2",
        minute=2,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            rows = provider_home_rows(app)
            assert rows[0] == ["[ALL]", "3", "3"]
            assert rows[1] == ["TechCrunch", "2", "2"]
            assert rows[2] == ["BBC News", "1", "1"]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_counts_only_translated_articles(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    pending = ArticleContent(
        article_id="bbc:pending-1",
        provider_id="bbc",
        provider_article_id="pending-1",
        url="https://example.com/bbc/pending-1",
        category="world",
        title="Pending BBC",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 1, tzinfo=UTC),
        body="Pending BBC body",
    )
    app.storage.upsert_article_source(pending)
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=2,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            rows = provider_home_rows(app)
            assert rows[0] == ["[ALL]", "2", "2"]
            assert rows[1] == ["BBC News", "1", "1"]
            assert rows[2] == ["TechCrunch", "1", "1"]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_uses_available_width_for_provider_column(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            table = provider_home_table(app)
            provider_column = list(table.columns.values())[0]
            assert provider_column.width > 12

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_hides_header_widget(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header = app.query_one("#article-header", Static)
            assert header.display is False

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_hides_selected_provider_summary_line(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert provider_home_footer_text(app) == ""

            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()

            assert provider_home_footer_text(app) == ""

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_shows_current_app_status(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            status = app.query_one("#status", Static)
            assert str(status.content) == "ready"

            app._set_status_text("fetching BBC News: World")
            app.refresh_view()
            await pilot.pause()
            assert str(status.content) == "fetching BBC News: World"

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_forwards_ctrl_p_to_command_palette(app_config, tmp_path, monkeypatch) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    calls: list[bool] = []

    def fake_command_palette() -> None:
        calls.append(True)

    monkeypatch.setattr(app, "action_command_palette", fake_command_palette)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("ctrl+p")
            await pilot.pause()
            assert calls == [True]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_hides_reader_only_bindings_from_footer(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert footer_bindings(app) == [
                ("c", "Sources", "show_source_manager"),
                ("d", "Download", "download_articles"),
                ("h", "Help", "show_help"),
                ("q", "Quit", "quit_reader"),
            ]

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_help_shows_provider_only_bindings(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("h")
            await pilot.pause()
            help_text = app.screen.query_one("#help-text", Static).content
            assert "Enter: open the selected provider" in help_text
            assert "C: manage sources" in help_text
            assert "D: download new articles" in help_text
            assert "Ctrl+P: command palette / choose theme" in help_text
            assert "Left/Right: previous/next article" not in help_text
            assert "S: toggle summary" not in help_text
            assert "M: more info" not in help_text
            assert "L: article list" not in help_text

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_entering_reader_can_trigger_auto_refresh(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    calls: list[object] = []

    def fake_launch_refresh_thread() -> object:
        calls.append(app._run_refresh)
        return object()

    app._launch_refresh_thread = fake_launch_refresh_thread  # type: ignore[method-assign]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(calls) == 1
            app.refresh_in_progress = False
            app._auto_fetch_armed = True

            await pilot.press("enter")
            await pilot.pause()

            assert provider_home_screen(app) is None
            assert len(calls) == 2
            assert app.refresh_in_progress is True

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_enter_all_opens_reader(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert provider_home_screen(app) is not None
            await pilot.press("enter")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert app.current_article is not None
            assert app.current_article.article_id == article_content.article_id

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_provider_scope_filters_articles_and_escape_returns_home(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body", minute=0)
    tech_article_id = seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert provider_home_screen(app) is None
            assert [article.provider_id for article in app.articles] == ["techcrunch"]
            assert app.current_article is not None
            assert app.current_article.article_id == tech_article_id

            await pilot.press("escape")
            await pilot.pause()
            assert provider_home_screen(app) is not None

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_scope_reader_state_is_independent(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    seed_provider_article(app, provider_id="bbc", provider_article_id="bbc-1", title="BBC 1", body="BBC body 1", minute=0)
    bbc_second = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-2",
        title="BBC 2",
        body="BBC body 2",
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=2,
    )
    tech_second = seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-2",
        title="TC 2",
        body="TC body 2",
        minute=3,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right")
            assert app.current_article is not None
            assert app.current_article.article_id == bbc_second
            await pilot.press("escape")
            await pilot.pause()

            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "TechCrunch"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right")
            assert app.current_article is not None
            assert app.current_article.article_id == tech_second
            await pilot.press("escape")
            await pilot.pause()

            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == bbc_second

            assert app.storage.load_reader_state("bbc").article_id == bbc_second
            assert app.storage.load_reader_state("techcrunch").article_id == tech_second

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_first_provider_entry_does_not_inherit_all_scope_article(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.set_provider_enabled("techcrunch", True)
    bbc_first = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-1",
        title="BBC 1",
        body="BBC body 1",
        minute=0,
    )
    bbc_second = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="bbc-2",
        title="BBC 2",
        body="BBC body 2",
        minute=1,
    )
    seed_provider_article(
        app,
        provider_id="techcrunch",
        provider_article_id="tc-1",
        title="TC 1",
        body="TC body 1",
        minute=2,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right")
            assert app.current_article is not None
            assert app.current_article.article_id == bbc_second

            await pilot.press("escape")
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert app.current_article is not None
            assert app.current_article.article_id == bbc_first
            assert app.storage.load_reader_state("bbc").article_id is None

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_scope_next_past_last_returns_home(app_config, tmp_path, article_content) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            provider_home_table(app).move_cursor(
                row=provider_home_row_index(app, "BBC News"),
                column=0,
                animate=False,
            )
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert provider_home_screen(app) is None

            await pilot.press("right")
            await pilot.pause()
            assert provider_home_screen(app) is not None

    asyncio.run(runner())


def test_ui_css_uses_textual_theme_tokens() -> None:
    assert "$background" in NewsReaderApp.CSS
    assert "$primary" in NewsReaderApp.CSS
    assert "$success" in NewsReaderApp.CSS
    assert "ansi_bright" not in NewsReaderApp.CSS
    assert "background: black;" not in NewsReaderApp.CSS


def test_ui_renders_russian_copy_and_preserves_hotkeys(app_config, tmp_path, article_content) -> None:
    app_config.ui.locale = "ru"
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Переведённый заголовок", "Переведённый текст", "done")
    app.storage.update_summary(article_content.article_id, "Краткая сводка", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            header = app.query_one("#article-header", Static).content
            assert "Статья № 1 из 1" in header
            assert "Заголовок: Переведённый заголовок" in header
            assert "Режим : полный" in header
            assert url_source(app) == f"URL: {article_content.url}"

            await pilot.press("h")
            await pilot.pause()
            help_text = app.screen.query_one("#help-text", Static).content
            assert "S: переключить сводку" in help_text
            assert "M: подробнее" in help_text
            assert "D: загрузить новые статьи" in help_text

            await pilot.press("s")
            await pilot.pause()
            summary_header = app.query_one("#article-header", Static).content
            assert "Режим : сводка" in summary_header
            assert body_source(app) == "Краткая сводка"

    asyncio.run(runner())
