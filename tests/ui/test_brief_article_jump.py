from __future__ import annotations

import asyncio

import pytest
from textual.widgets import Input, Static

from newsr.brief import BriefPeriod
from newsr.domain import ViewMode
from newsr.export import ExportAction
from newsr.ui import BriefArticleJumpScreen, NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
from tests.ui.support.fakes import FakeBriefLLM, FakeExportService
from tests.ui.support.provider_home import provider_home_row_index, provider_home_rows
from tests.ui.support.reader import body_source, header_text
from tests.ui.support.screens import (
    brief_reader_body,
    brief_reader_pane,
    brief_reader_screen,
    brief_screen,
    export_screen,
)


def brief_article_jump_screen(app: NewsReaderApp) -> BriefArticleJumpScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, BriefArticleJumpScreen):
            return screen
    return None


def brief_article_jump_input(app: NewsReaderApp) -> Input:
    screen = brief_article_jump_screen(app)
    assert screen is not None
    return screen.query_one("#brief-article-jump-input", Input)


def brief_article_jump_error(app: NewsReaderApp) -> str:
    screen = brief_article_jump_screen(app)
    assert screen is not None
    return str(screen.query_one("#brief-article-jump-error", Static).content)


@pytest.mark.provider_home
def test_ui_brief_reader_number_jump_uses_default_mode_and_saves_explicit_provider_mode(
    app_config, tmp_path
) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.llm_client = FakeBriefLLM("# Brief\n\nGenerated provider report [2]\n\nOther report item [1]")  # type: ignore[assignment]
    fake_export = FakeExportService()
    app.export_service = fake_export
    first_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-jump-1",
        title="Brief jump one",
        body="Translated body one",
        minute=1,
    )
    second_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-jump-2",
        title="Brief jump two",
        body="Translated body two",
        minute=2,
    )
    assert app.storage.load_reader_state("bbc").article_id is None
    assert app.storage.load_reader_state("[ALL]").article_id is None

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            screen = brief_screen(app)
            assert screen is not None
            screen.period = BriefPeriod.ALL_UNREAD
            screen.mark_read = False
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                if brief_reader_screen(app) is not None:
                    break
            else:
                raise AssertionError("brief reader was not opened")

            assert "Generated provider report [1]" in brief_reader_body(app)

            await pilot.press("1")
            await pilot.pause()
            assert brief_article_jump_screen(app) is not None
            assert brief_article_jump_input(app).value == "1"

            await pilot.press("enter")
            await pilot.pause()
            assert brief_article_jump_screen(app) is None
            assert brief_reader_screen(app) is None
            assert app.provider_home_open is False
            assert app.current_article is not None
            assert app.current_article.article_id == second_id
            assert body_source(app) == "Translated body two"
            assert "Article # 1 of 2" in header_text(app)
            bbc_state = app.storage.load_reader_state("bbc")
            assert bbc_state.article_id is None
            assert bbc_state.view_mode == ViewMode.FULL

            await pilot.press("left", "right")
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == second_id

            await pilot.press("s")
            await pilot.pause()
            assert app.active_reader_state.view_mode == ViewMode.SUMMARY
            assert body_source(app) == "Summary for Brief jump two"
            bbc_state = app.storage.load_reader_state("bbc")
            assert bbc_state.article_id is None
            assert bbc_state.view_mode == ViewMode.SUMMARY

            await pilot.press("e")
            await pilot.pause()
            assert export_screen(app) is not None
            await pilot.press("2")
            await pilot.pause()
            assert fake_export.calls == [(ExportAction.COPY_PNG, second_id, ViewMode.SUMMARY, app.theme)]

            await pilot.press("escape")
            await pilot.pause()
            assert brief_reader_screen(app) is not None
            assert "Generated provider report [1]" in brief_reader_body(app)
            assert app.provider_home_open is True
            assert app.storage.load_reader_state("bbc").article_id is None
            assert app.storage.load_reader_state("bbc").view_mode == ViewMode.SUMMARY
            assert app.storage.load_reader_state("[ALL]").article_id is None
            assert app.storage.load_reader_state("[ALL]").view_mode == ViewMode.FULL
            assert first_id != second_id

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_reader_number_jump_inherits_article_provider_mode(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.llm_client = FakeBriefLLM("# Brief\n\nGenerated provider report [1]")  # type: ignore[assignment]
    article_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-provider-mode",
        title="Brief provider mode",
        body="Original provider body",
        minute=1,
    )
    app.storage.update_translation(
        article_id,
        "Translated provider title",
        "Translated provider body",
        "done",
    )
    app.storage.save_reader_state(
        "bbc",
        app.reader_state.__class__(
            article_id=None,
            view_mode=ViewMode.ORIGINAL,
            scroll_offset=11,
        ),
    )
    app.storage.save_reader_state(
        "[ALL]",
        app.reader_state.__class__(
            article_id=None,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        ),
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            screen = brief_screen(app)
            assert screen is not None
            screen.period = BriefPeriod.ALL_UNREAD
            screen.mark_read = False
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                if brief_reader_screen(app) is not None:
                    break
            else:
                raise AssertionError("brief reader was not opened")

            await pilot.press("1")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert app.current_article is not None
            assert app.current_article.article_id == article_id
            assert app.active_reader_state.view_mode == ViewMode.ORIGINAL
            assert body_source(app) == "Original provider body"
            bbc_state = app.storage.load_reader_state("bbc")
            assert bbc_state.article_id is None
            assert bbc_state.view_mode == ViewMode.ORIGINAL
            assert bbc_state.scroll_offset == 11
            assert app.storage.load_reader_state("[ALL]").view_mode == ViewMode.FULL

            await pilot.press("escape")
            await pilot.pause()
            assert brief_reader_screen(app) is not None
            bbc_state = app.storage.load_reader_state("bbc")
            assert bbc_state.article_id is None
            assert bbc_state.view_mode == ViewMode.ORIGINAL
            assert bbc_state.scroll_offset == 11

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_mark_read_survives_article_jump_from_active_provider(app_config, tmp_path) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.llm_client = FakeBriefLLM("# Brief\n\nGenerated provider report [2]\n\nOther report item [1]")  # type: ignore[assignment]
    first_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-active-provider-1",
        title="Brief active provider one",
        body="Translated body one",
        minute=1,
    )
    second_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-active-provider-2",
        title="Brief active provider two",
        body="Translated body two",
        minute=2,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            app.open_scope("bbc")
            await pilot.pause()
            assert app.provider_home_open is False
            assert app.storage.load_reader_state("bbc").article_id is None

            await pilot.press("s")
            await pilot.pause()
            assert app.reader_state.view_mode == ViewMode.SUMMARY

            app.action_return_to_provider_home()
            await pilot.pause()
            assert app.provider_home_open is True
            assert app.storage.load_reader_state("bbc").article_id == first_id

            await pilot.press("b")
            await pilot.pause()
            screen = brief_screen(app)
            assert screen is not None
            screen.period = BriefPeriod.ALL_UNREAD
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                if brief_reader_screen(app) is not None:
                    break
            else:
                raise AssertionError("brief reader was not opened")
            bbc_state = app.storage.load_reader_state("bbc")
            assert bbc_state.article_id == second_id
            assert bbc_state.view_mode == ViewMode.SUMMARY

            await pilot.press("1")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert app.current_article is not None
            assert app.current_article.article_id == second_id
            assert app.active_reader_state.view_mode == ViewMode.SUMMARY
            assert body_source(app) == "Summary for Brief active provider two"

            await pilot.press("s")
            await pilot.pause()
            assert app.active_reader_state.view_mode == ViewMode.ORIGINAL
            bbc_state = app.storage.load_reader_state("bbc")
            assert bbc_state.article_id == second_id
            assert bbc_state.view_mode == ViewMode.ORIGINAL

            await pilot.press("escape")
            await pilot.pause()
            assert brief_reader_screen(app) is not None
            assert app.reader_state.view_mode == ViewMode.ORIGINAL

    asyncio.run(runner())

    restarted = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(restarted)

    async def restart_runner() -> None:
        async with restarted.run_test() as pilot:
            await pilot.pause()
            bbc_state = restarted.storage.load_reader_state("bbc")
            assert bbc_state.article_id == second_id
            assert bbc_state.view_mode == ViewMode.ORIGINAL
            bbc_row = provider_home_rows(restarted)[provider_home_row_index(restarted, "BBC News")]
            assert bbc_row[1] == "0"

    asyncio.run(restart_runner())


@pytest.mark.provider_home
def test_ui_brief_article_jump_rejects_out_of_range_numbers(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.llm_client = FakeBriefLLM("# Brief\n\nGenerated provider report [1]")  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-jump-invalid",
        title="Brief jump invalid",
        body="Translated body",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            screen = brief_screen(app)
            assert screen is not None
            screen.period = BriefPeriod.ALL_UNREAD
            screen.mark_read = False
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                if brief_reader_screen(app) is not None:
                    break
            else:
                raise AssertionError("brief reader was not opened")

            await pilot.press("2")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert brief_article_jump_screen(app) is not None
            assert brief_article_jump_error(app) == "Choose a number from 1 to 1."

            await pilot.press("escape")
            await pilot.pause()
            assert brief_article_jump_screen(app) is None
            assert brief_reader_screen(app) is not None

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_reader_restores_scroll_after_article_jump(app_config, tmp_path) -> None:
    report = "# Brief\n\n[1]\n\n" + "\n\n".join(f"Paragraph {index} [1]" for index in range(120))
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    disable_startup_refresh(app)
    app.llm_client = FakeBriefLLM(report)  # type: ignore[assignment]
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-jump-scroll",
        title="Brief jump scroll",
        body="Translated body",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("b")
            await pilot.pause()
            screen = brief_screen(app)
            assert screen is not None
            screen.period = BriefPeriod.ALL_UNREAD
            screen.mark_read = False
            app.generate_brief()
            for _ in range(20):
                await pilot.pause()
                if brief_reader_screen(app) is not None:
                    break
            else:
                raise AssertionError("brief reader was not opened")

            pane = brief_reader_pane(app)
            pane.scroll_to(y=18, animate=False)
            await pilot.pause()
            saved_offset = int(pane.scroll_y)
            assert saved_offset > 0

            await pilot.press("1")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert brief_reader_screen(app) is None

            await pilot.press("escape")
            for _ in range(30):
                await pilot.pause()
                reader = brief_reader_screen(app)
                if reader is not None and int(brief_reader_pane(app).scroll_y) == saved_offset:
                    break
            else:
                raise AssertionError("brief reader scroll offset was not restored")

    asyncio.run(runner())
