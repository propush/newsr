from __future__ import annotations

import asyncio

import pytest

from newsr.brief import BriefPeriod
from newsr.domain import PlaylistItem, ReaderState, ViewMode

from tests.ui.support.app_state import seed_provider_article
from tests.ui.support.fakes import FakeBriefLLM
from tests.ui.support.playlist import build_app, wait_for
from tests.ui.support.provider_home import provider_home_row_index, provider_home_rows
from tests.ui.support.screens import brief_reader_screen, brief_screen


def _unread(app, display_name: str) -> str:
    return provider_home_rows(app)[provider_home_row_index(app, display_name)][1]


@pytest.mark.provider_home
def test_ui_provider_home_shift_a_queues_unread_articles_in_provider_home_row_order(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    app.storage.set_provider_enabled("techcrunch", True)

    def seed(provider_id: str, key: str, minute: int) -> str:
        return seed_provider_article(
            app,
            provider_id=provider_id,
            provider_article_id=key,
            title=key,
            body=f"Body {key}.",
            minute=minute,
        )

    bbc_1 = seed("bbc", "bbc-1", 1)
    tc_1 = seed("techcrunch", "tc-1", 2)
    bbc_2 = seed("bbc", "bbc-2", 3)
    seed("arstechnica", "ars-1", 4)
    tc_2 = seed("techcrunch", "tc-2", 5)
    bbc_3 = seed("bbc", "bbc-3", 6)
    tc_3 = seed("techcrunch", "tc-3", 7)
    app.storage.save_reader_state("bbc", ReaderState(article_id=bbc_1, view_mode=ViewMode.FULL, scroll_offset=0))

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.provider_home_open is True
            assert app.check_action("playlist_add_rest", ()) is True
            assert app.check_action("playlist_add_current", ()) is False
            assert provider_home_row_index(app, "TechCrunch") < provider_home_row_index(app, "BBC News")

            await pilot.press("A")
            await pilot.pause()
            expected = [
                PlaylistItem(tc_1, "techcrunch"),
                PlaylistItem(tc_2, "techcrunch"),
                PlaylistItem(tc_3, "techcrunch"),
                PlaylistItem(bbc_2, "bbc"),
                PlaylistItem(bbc_3, "bbc"),
            ]
            assert app._playlist.items == expected
            assert app.storage.load_playlist() == expected
            assert "added 5 to playlist" in app.status_text

            await pilot.press("A")
            await pilot.press("a")
            await pilot.pause()
            assert app._playlist.items == expected
            assert "added 0 to playlist" in app.status_text

            await pilot.press("p")
            await wait_for(pilot, lambda: not app._playlist.items and not app._playlist.is_running)
            assert app.storage.load_reader_state("bbc").article_id == bbc_3
            assert app.storage.load_reader_state("techcrunch").article_id == tc_3
            assert app.storage.load_reader_state("[ALL]").article_id is None
            await wait_for(pilot, lambda: _unread(app, "BBC News") == "0" and _unread(app, "TechCrunch") == "0")

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_brief_reader_shift_a_queues_brief_articles_without_marking_them_read(app_config, tmp_path) -> None:
    app, output, _engine = build_app(app_config, tmp_path)
    app.llm_client = FakeBriefLLM("# Brief\n\nGenerated provider report [2]\n\nOther report item [1]")  # type: ignore[assignment]
    first_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-1",
        title="Brief one",
        body="Body one.",
        minute=1,
    )
    second_id = seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="brief-2",
        title="Brief two",
        body="Body two.",
        minute=2,
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
            await wait_for(pilot, lambda: brief_reader_screen(app) is not None)

            await pilot.press("A")
            await pilot.pause()
            expected = [
                PlaylistItem(second_id, "bbc", mark_read=False),
                PlaylistItem(first_id, "bbc", mark_read=False),
            ]
            assert app._playlist.items == expected
            assert app.storage.load_playlist() == expected
            assert brief_reader_screen(app) is not None
            assert any("added 2 to playlist" in str(notice.message) for notice in app._notifications)

            await pilot.press("escape")
            await pilot.pause()
            assert brief_reader_screen(app) is None
            await pilot.press("p")
            await wait_for(pilot, lambda: not app._playlist.items and not app._playlist.is_running)
            assert "Body two." in output.played
            assert "Body one." in output.played
            assert app.storage.load_reader_state("bbc").article_id is None
            assert app.storage.load_reader_state("[ALL]").article_id is None
            assert _unread(app, "BBC News") == "2"

    asyncio.run(runner())
