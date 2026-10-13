from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from textual.widgets import DataTable, Static

from newsr.domain import PlaylistItem, ReaderState, ViewMode
from newsr.ui import NewsReaderApp
from newsr.ui.screens import ConfirmDialogScreen, HelpScreen, PlaylistScreen

from tests.tts.fakes import FakeAudioOutput, FakeTTSEngine
from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
from tests.ui.support.provider_home import provider_home_row_index, provider_home_rows
from tests.ui.support.reader import plain_content


def build_app(
    app_config,
    tmp_path,
    *,
    output: FakeAudioOutput | None = None,
    engine: FakeTTSEngine | None = None,
) -> tuple[NewsReaderApp, FakeAudioOutput, FakeTTSEngine]:
    output = output or FakeAudioOutput()
    engine = engine or FakeTTSEngine()
    app = NewsReaderApp(
        app_config,
        tmp_path / "newsr.sqlite3",
        audio_output_factory=lambda: output,
        tts_engine_factory=lambda _config: engine,
    )
    disable_startup_refresh(app)
    return app, output, engine


def seed_articles(app: NewsReaderApp, count: int, *, provider_id: str = "bbc") -> list[str]:
    return [
        seed_provider_article(
            app,
            provider_id=provider_id,
            provider_article_id=f"{provider_id}-{index}",
            title=f"Title {index}",
            body=f"Body {index}.",
            minute=index,
        )
        for index in range(1, count + 1)
    ]


async def wait_for(pilot, predicate: Callable[[], bool], *, attempts: int = 200) -> None:
    for _ in range(attempts):
        if predicate():
            return
        await pilot.pause(0.01)
    raise AssertionError("condition was not reached")


def playback_status(app: NewsReaderApp) -> str:
    widget = app.query_one("#playback-status", Static)
    return plain_content(widget.content) if widget.display else ""


def test_ui_playlist_adds_current_and_following_articles_without_duplicates(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    article_ids = seed_articles(app, 4)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.press("right", "right")
            await pilot.press("A")
            await pilot.press("a")
            await pilot.pause()

            expected = [PlaylistItem(article_id, "[ALL]") for article_id in (article_ids[0], *article_ids[2:])]
            assert app._playlist.items == expected
            assert app.storage.load_playlist() == expected
            assert "3 queued" in playback_status(app)

    asyncio.run(runner())


def test_ui_playlist_plays_items_marks_them_read_and_empties_queue(app_config, tmp_path) -> None:
    app, output, engine = build_app(app_config, tmp_path)
    article_ids = seed_articles(app, 3)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A")
            await pilot.press("p")
            await wait_for(pilot, lambda: not app._playlist.items and not app._playlist.is_running)

            assert output.played[:3] == [
                "BBC News. Article 1 of 3.",
                "Title 1.",
                "Body 1.",
            ]
            assert ("BBC News. Article 3 of 3.", "en") in engine.calls
            assert ("Title 3.", "ru") in engine.calls
            assert app.current_article is not None
            assert app.current_article.article_id == article_ids[2]
            assert app.storage.load_reader_state("[ALL]").article_id == article_ids[2]
            assert app.storage.load_playlist() == []
            assert playback_status(app) == ""

    asyncio.run(runner())


def test_ui_playlist_reads_current_view_mode(app_config, tmp_path) -> None:
    app, output, _engine = build_app(app_config, tmp_path)
    seed_articles(app, 1)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("s")
            await pilot.press("a", "p")
            await wait_for(pilot, lambda: not app._playlist.is_running)

            assert app.reader_state.view_mode == ViewMode.SUMMARY
            assert output.played[-1] == "Summary for Title 1."

    asyncio.run(runner())


def test_ui_playlist_pause_screen_remove_and_clear(app_config, tmp_path) -> None:
    app, output, _engine = build_app(app_config, tmp_path, output=FakeAudioOutput(auto_finish=False))
    article_ids = seed_articles(app, 3)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 3."])
            assert playback_status(app).startswith("▶ Title 1")

            await pilot.press("p")
            await pilot.pause()
            assert output.paused is True
            assert playback_status(app).startswith("‖ Title 1")

            await pilot.press("P")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, PlaylistScreen)
            table = screen.query_one("#playlist-table", DataTable)
            assert table.row_count == 3
            assert table.get_row_at(0)[0] == "‖"
            assert "paused" in plain_content(screen.query_one("#playlist-header", Static).content)

            await pilot.press("down", "x")
            await pilot.pause()
            assert [item.article_id for item in app._playlist.items] == [article_ids[0], article_ids[2]]
            assert table.row_count == 2

            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmDialogScreen)
            await pilot.press("y")
            await pilot.pause()
            assert app._playlist.items == []
            assert app._playlist.is_running is False
            assert app.storage.load_playlist() == []

            await pilot.press("escape")
            await pilot.pause()
            assert len(app.screen_stack) == 1

    asyncio.run(runner())


def test_ui_playlist_enter_plays_selected_item_now(app_config, tmp_path) -> None:
    app, output, _engine = build_app(app_config, tmp_path, output=FakeAudioOutput(auto_finish=False))
    article_ids = seed_articles(app, 3)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 3."])
            await pilot.press("P")
            await pilot.pause()
            await pilot.press("down", "down", "enter")
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 3 of 3."])

            assert [item.article_id for item in app._playlist.items] == [
                article_ids[2],
                article_ids[0],
                article_ids[1],
            ]
            app._playlist.clear()

    asyncio.run(runner())


def test_ui_playlist_next_and_previous_keys(app_config, tmp_path) -> None:
    app, output, _engine = build_app(app_config, tmp_path, output=FakeAudioOutput(auto_finish=False))
    article_ids = seed_articles(app, 2)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 2."])
            output.release()
            await wait_for(pilot, lambda: output.played[-1:] == ["Title 1."])

            await pilot.press("left_square_bracket")
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 1 of 2."])

            await pilot.press("right_square_bracket")
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 2 of 2."])
            assert [item.article_id for item in app._playlist.items] == [article_ids[1]]
            assert app.current_article is not None
            assert app.current_article.article_id == article_ids[1]

            await pilot.press("left_square_bracket")
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 1 of 2."])
            assert [item.article_id for item in app._playlist.items] == article_ids
            assert app.current_article.article_id == article_ids[1]
            app._playlist.clear()

    asyncio.run(runner())


def test_ui_playlist_moves_other_scope_position_forward_only(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    article_ids = seed_articles(app, 3)
    app.storage.save_reader_state("bbc", ReaderState(article_id=article_ids[0], view_mode=ViewMode.FULL, scroll_offset=0))
    app.storage.save_playlist([PlaylistItem(article_ids[1], "bbc")])
    app._playlist.load()

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("p")
            await wait_for(pilot, lambda: not app._playlist.is_running)
            assert app.storage.load_reader_state("bbc").article_id == article_ids[1]
            assert app.current_article is not None
            assert app.current_article.article_id == article_ids[0]

            app.storage.save_reader_state(
                "bbc", ReaderState(article_id=article_ids[2], view_mode=ViewMode.FULL, scroll_offset=0)
            )
            app._playlist._items = [PlaylistItem(article_ids[1], "bbc")]
            await pilot.press("p")
            await wait_for(pilot, lambda: not app._playlist.is_running)
            assert app.storage.load_reader_state("bbc").article_id == article_ids[2]

    asyncio.run(runner())


def test_ui_playlist_defers_reader_move_while_overlay_is_open(app_config, tmp_path) -> None:
    app, output, _engine = build_app(app_config, tmp_path, output=FakeAudioOutput(auto_finish=False))
    article_ids = seed_articles(app, 2)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 2."])
            await pilot.press("h")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)

            output.release(3)
            await wait_for(pilot, lambda: output.played[-1:] == ["BBC News. Article 2 of 2."])
            assert app.current_article is not None
            assert app.current_article.article_id == article_ids[0]

            await pilot.press("escape")
            await wait_for(
                pilot,
                lambda: app.current_article is not None and app.current_article.article_id == article_ids[1],
            )
            app._playlist.clear()

    asyncio.run(runner())


def test_ui_playlist_synthesis_error_keeps_queue(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path, engine=FakeTTSEngine(fail_on="Body 1"))
    article_ids = seed_articles(app, 2)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: not app._playlist.is_running)

            assert [item.article_id for item in app._playlist.items] == article_ids
            assert playback_status(app) == "⚠ TTS: cannot speak Body 1"

    asyncio.run(runner())


def test_ui_playlist_is_restored_after_restart(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    article_ids = seed_articles(app, 2)

    async def first_run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A")
            await pilot.press("q")

    asyncio.run(first_run())

    restarted, _output, _engine = build_app(app_config, tmp_path)

    async def second_run() -> None:
        async with restarted.run_test() as pilot:
            await pilot.pause()
            assert [item.article_id for item in restarted._playlist.items] == article_ids
            assert playback_status(restarted) == "■ playlist: 2 queued"

    asyncio.run(second_run())


@pytest.mark.provider_home
def test_ui_provider_home_allows_playback_keys_and_hides_add_keys(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    seed_articles(app, 1)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.provider_home_open is True
            assert app.check_action("toggle_playback", ()) is True
            assert app.check_action("show_playlist", ()) is True
            assert app.check_action("playlist_add_current", ()) is False
            assert app.check_action("playlist_add_rest", ()) is False

            await pilot.press("P")
            await pilot.pause()
            assert isinstance(app.screen, PlaylistScreen)

    asyncio.run(runner())


@pytest.mark.provider_home
def test_ui_provider_home_counters_drop_after_playlist_screen_closes(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    article_ids = seed_articles(app, 3)
    app.storage.save_playlist([PlaylistItem(article_ids[1], "[ALL]"), PlaylistItem(article_ids[0], "bbc")])
    app._playlist.load()

    def unread(display_name: str) -> str:
        return provider_home_rows(app)[provider_home_row_index(app, display_name)][1]

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert unread("[ALL]") == "3"
            assert unread("BBC News") == "3"

            await pilot.press("P")
            await pilot.pause()
            await pilot.press("p")
            await wait_for(pilot, lambda: not app._playlist.is_running)
            assert unread("BBC News") == "2"
            assert unread("[ALL]") == "3"

            await pilot.press("escape")
            await wait_for(pilot, lambda: unread("[ALL]") == "1")
            assert app.storage.load_reader_state("[ALL]").article_id == article_ids[1]

    asyncio.run(runner())


def test_ui_playlist_renders_titles_with_markup_characters_literally(app_config, tmp_path) -> None:
    app, output, _engine = build_app(app_config, tmp_path, output=FakeAudioOutput(auto_finish=False))
    seed_provider_article(
        app,
        provider_id="bbc",
        provider_article_id="markup",
        title="Title [/bold] and [Video]",
        body="Body.",
        minute=1,
    )

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 1."])
            await pilot.pause()
            assert "Title [/bold] and [Video]" in playback_status(app)

            await pilot.press("P")
            await pilot.pause()
            table = app.screen.query_one("#playlist-table", DataTable)
            assert table.get_row_at(0)[2].plain == "Title [/bold] and [Video]"
            app._playlist.clear()

    asyncio.run(runner())


def test_ui_playlist_saves_progress_for_the_already_selected_article(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    article_ids = seed_articles(app, 2)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.storage.load_reader_state("[ALL]").article_id is None
            await pilot.press("a", "p")
            await wait_for(pilot, lambda: not app._playlist.is_running)

            assert app.current_article is not None
            assert app.current_article.article_id == article_ids[0]
            assert app.storage.load_reader_state("[ALL]").article_id == article_ids[0]

    asyncio.run(runner())


def test_ui_playlist_keeps_the_furthest_deferred_position(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    article_ids = seed_articles(app, 3)
    app.storage.save_playlist([PlaylistItem(article_ids[2], "[ALL]"), PlaylistItem(article_ids[1], "[ALL]")])
    app._playlist.load()

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("h")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            app._playlist.toggle_play()
            await wait_for(pilot, lambda: not app._playlist.is_running)
            assert app.current_article is not None
            assert app.current_article.article_id == article_ids[0]

            await pilot.press("escape")
            await wait_for(
                pilot,
                lambda: app.current_article is not None and app.current_article.article_id == article_ids[2],
            )
            assert app.storage.load_reader_state("[ALL]").article_id == article_ids[2]

    asyncio.run(runner())


def test_ui_playlist_screen_keeps_selection_when_an_item_finishes(app_config, tmp_path) -> None:
    app, output, _engine = build_app(app_config, tmp_path, output=FakeAudioOutput(auto_finish=False))
    article_ids = seed_articles(app, 3)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A", "p")
            await wait_for(pilot, lambda: output.played == ["BBC News. Article 1 of 3."])
            await pilot.press("P")
            await pilot.pause()
            await pilot.press("down")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, PlaylistScreen)
            assert screen.selected_article_id == article_ids[1]

            output.release(3)
            await wait_for(pilot, lambda: len(app._playlist.items) == 2)
            await pilot.pause()
            assert screen.selected_article_id == article_ids[1]
            app._playlist.clear()

    asyncio.run(runner())


def test_playlist_builds_default_engine_with_app_llm_client(app_config, tmp_path, monkeypatch) -> None:
    calls: list[tuple[object, object]] = []
    engine = FakeTTSEngine()

    def fake_build(config, *, llm=None):  # type: ignore[no-untyped-def]
        calls.append((config, llm))
        return engine

    monkeypatch.setattr("newsr.ui.controllers.playlist.build_tts_engine", fake_build)
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3", audio_output_factory=FakeAudioOutput)
    disable_startup_refresh(app)

    assert app._playlist._engine_instance() is engine
    assert app._playlist._engine_instance() is engine
    assert calls == [(app_config.tts, app.llm_client)]
