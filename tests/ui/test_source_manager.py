from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from rich.text import Text
from textual.widgets import Static

from newsr.domain import ArticleContent, ProviderTarget
from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import article_pane
from tests.ui.support.source_manager import (
    category_screen,
    provider_list,
    provider_row_index,
    provider_rows,
    target_list,
    wait_for_source_manager,
)


def provider_row_cells(app: NewsReaderApp, row_index: int) -> list[object]:
    table = provider_list(app)
    return list(table.get_row_at(row_index))


def provider_data_rows(app: NewsReaderApp) -> list[list[str]]:
    return [row for row in provider_rows(app) if row and row[0] in {"[x]", "[ ]"}]


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


def test_ui_reader_navigation_still_works_after_source_manager(app_config, tmp_path, article_content) -> None:
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

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("c")
            await wait_for_source_manager(app, pilot)
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


def test_ui_source_manager_loads_current_provider_and_targets(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    expected_selected = sum(
        len(app.storage.list_selected_targets(provider.provider_id))
        for provider in app.storage.list_providers()
    )

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
                for row in provider_data_rows(app)
            }
            assert provider_statuses["BBC News"] == "[x]"
            assert provider_statuses["TechCrunch"] == "[ ]"
            assert provider_statuses["The Hacker News"] == "[ ]"
            assert provider_statuses["Ars Technica"] == "[ ]"
            assert len(provider_statuses) == len(app.storage.list_providers())
            assert [row[1] for row in provider_rows(app)[:2]] == ["Providers", "9to5Google"]

            provider_list(app).move_cursor(row=provider_row_index(app, "BBC News"), column=0, animate=False)
            await pilot.pause()
            assert target_rows(app)[:4] == [
                ["[x]", "World"],
                ["[x]", "Technology"],
                ["[x]", "Business"],
                ["[x]", "Entertainment & Arts"],
            ]
            status_text = source_status_text(app)
            assert f"Loaded {len(app.storage.list_providers())} providers." in status_text
            assert "Enabled 1." in status_text
            assert f"Selected {expected_selected} targets globally." in status_text

    asyncio.run(runner())


def test_ui_source_manager_status_counts_selected_targets_across_providers_and_topics(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    selected_before = sum(
        len(app.storage.list_selected_targets(provider.provider_id))
        for provider in app.storage.list_providers()
    )
    app.storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )
    app.rebuild_provider_registry()

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

            status_text = source_status_text(app)
            assert f"Loaded {len(app.storage.list_providers())} providers." in status_text
            assert "Enabled 2." in status_text
            assert f"Selected {selected_before + 1} targets globally." in status_text

    asyncio.run(runner())


def test_ui_source_manager_toggling_provider_keeps_cursor_position(app_config, tmp_path) -> None:
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

            techcrunch_row = provider_row_index(app, "TechCrunch")
            provider_list(app).move_cursor(row=techcrunch_row, column=0, animate=False)
            await pilot.pause()

            assert provider_list(app).cursor_row == techcrunch_row
            await pilot.press("space")
            await pilot.pause()

            assert provider_list(app).cursor_row == techcrunch_row
            provider_statuses = {
                row[1]: row[0]
                for row in provider_data_rows(app)
            }
            assert provider_statuses["TechCrunch"] == "[x]"

    asyncio.run(runner())


def test_ui_source_manager_toggling_provider_keeps_cursor_position_after_idle_cycles(app_config, tmp_path) -> None:
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

            techcrunch_row = provider_row_index(app, "TechCrunch")
            provider_table = provider_list(app)
            provider_table.focus()
            await pilot.pause()
            while provider_table.cursor_row < techcrunch_row:
                await pilot.press("down")
                await pilot.pause()

            assert provider_table.cursor_row == techcrunch_row
            await pilot.press("space")
            for _ in range(5):
                await pilot.pause()

            assert provider_table.cursor_row == techcrunch_row
            provider_statuses = {
                row[1]: row[0]
                for row in provider_data_rows(app)
            }
            assert provider_statuses["TechCrunch"] == "[x]"

    asyncio.run(runner())


def test_ui_source_manager_groups_topics_and_sorts_by_name_within_groups(app_config, tmp_path) -> None:
    app_config.ui.provider_sort.primary = "unread"
    app_config.ui.provider_sort.direction = "desc"
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.storage.create_topic_provider(
        display_name="Zed AI",
        topic_query="Zed AI",
        update_schedule=None,
    )
    app.storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )
    app.rebuild_provider_registry()

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

            rows = provider_rows(app)
            labels = [row[1] for row in rows]
            topics_index = labels.index("Topics")
            providers_header = provider_row_cells(app, 0)[1]
            topics_header = provider_row_cells(app, topics_index)[1]

            assert isinstance(providers_header, Text)
            assert providers_header.justify == "center"
            assert providers_header.style == "dim italic $secondary"
            assert isinstance(topics_header, Text)
            assert topics_header.justify == "center"
            assert topics_header.style == "dim italic $secondary"
            assert labels[0] == "Providers"
            assert labels[topics_index + 1 : topics_index + 3] == ["OpenAI policy", "Zed AI"]
            assert "Virtual" not in labels
            assert labels[1:topics_index] == sorted(labels[1:topics_index], key=str.casefold)
            assert all(len(row) == 4 for row in provider_rows(app))

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
                ["[x]", "Entertainment & Arts"],
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


def test_ui_source_manager_hides_common_key_hints(app_config, tmp_path) -> None:
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

            bindings = {binding.key: binding for _key, binding in screen._bindings}
            assert bindings["escape"].show is False
            assert bindings["tab"].show is False
            assert bindings["r"].show is False
            assert bindings["space"].show is False
            assert str(screen.query_one("#source-hint", Static).content) == (
                "Space: toggle   U: edit schedule   X: delete topic   A: apply"
            )

    asyncio.run(runner())


def test_ui_source_manager_provider_columns_fit_split_layout(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)

    async def runner() -> None:
        async with app.run_test(size=(84, 28)) as pilot:
            await pilot.press("c")
            for _ in range(20):
                await pilot.pause()
                screen = category_screen(app)
                if screen is not None and provider_list(app).row_count and target_list(app).row_count:
                    break
            else:
                raise AssertionError("source manager did not finish loading")

            table = provider_list(app)
            rendered_width = sum(column.width for column in table.ordered_columns) + (
                len(table.ordered_columns) * (2 * table.cell_padding)
            )
            assert rendered_width <= table.size.width

    asyncio.run(runner())
