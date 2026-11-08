from __future__ import annotations

import asyncio

from tests.tts.fakes import FakePreparingTTSEngine
from tests.ui.support.playlist import build_app, playback_status, seed_articles, wait_for


def test_ui_playlist_prepares_every_reader_mode_when_articles_are_added(app_config, tmp_path) -> None:
    engine = FakePreparingTTSEngine()
    app, _output, _engine = build_app(app_config, tmp_path, engine=engine)
    seed_articles(app, 2)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await wait_for(pilot, lambda: len(engine.prepared) == 1 and app._playlist.preparing_count == 0)
            await pilot.press("A")
            await wait_for(pilot, lambda: len(engine.prepared) == 2 and app._playlist.preparing_count == 0)

            first, second = engine.prepared
            assert len(set(first)) == len(first)
            assert {
                ("BBC News. Article 1 of 2.", "en"),
                ("Title 1.", "ru"),
                ("Body 1.", "ru"),
                ("Summary for Title 1.", "ru"),
            } <= set(first)
            assert ("Summary for Title 2.", "ru") in second
            assert engine.calls == []

    asyncio.run(runner())


def test_ui_playlist_status_shows_preparation_until_it_finishes(app_config, tmp_path) -> None:
    engine = FakePreparingTTSEngine(blocked=True)
    app, _output, _engine = build_app(app_config, tmp_path, engine=engine)
    seed_articles(app, 3)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A")
            await wait_for(pilot, engine.preparing.is_set)

            assert playback_status(app) == "■ playlist: 3 queued, preparing 3"
            engine.gate.set()
            await wait_for(pilot, lambda: playback_status(app) == "■ playlist: 3 queued")

    asyncio.run(runner())


def test_ui_playlist_playback_waits_for_preparation(app_config, tmp_path) -> None:
    engine = FakePreparingTTSEngine(blocked=True)
    app, output, _engine = build_app(app_config, tmp_path, engine=engine)
    seed_articles(app, 1)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a", "p")
            await wait_for(pilot, lambda: playback_status(app).startswith("…"))

            assert app._playlist.status_text(200) == "… Title 1 · BBC News · 1 queued, preparing 1"
            assert engine.calls == []
            assert output.played == []
            engine.gate.set()
            await wait_for(pilot, lambda: not app._playlist.is_running)

            assert output.played[:2] == ["BBC News. Article 1 of 1.", "Title 1."]

    asyncio.run(runner())


def test_ui_playlist_prepares_queued_articles_again_when_their_text_changes(app_config, tmp_path) -> None:
    engine = FakePreparingTTSEngine()
    app, _output, _engine = build_app(app_config, tmp_path, engine=engine)
    article_ids = seed_articles(app, 2)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await wait_for(pilot, lambda: len(engine.prepared) == 1 and app._playlist.preparing_count == 0)

            app.storage.update_summary(article_ids[0], "Summary about Cerebras", "done")
            app._refresh._load_ready_article(article_ids[0])
            app._refresh._load_ready_article(article_ids[1])
            await wait_for(pilot, lambda: len(engine.prepared) == 2 and app._playlist.preparing_count == 0)
            await pilot.pause(0.05)

            assert len(engine.prepared) == 2
            assert ("Summary about Cerebras.", "ru") in engine.prepared[1]

    asyncio.run(runner())


def test_ui_playlist_remove_and_clear_drop_pending_preparation(app_config, tmp_path) -> None:
    engine = FakePreparingTTSEngine(blocked=True)
    app, _output, _engine = build_app(app_config, tmp_path, engine=engine)
    article_ids = seed_articles(app, 3)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A")
            await wait_for(pilot, engine.preparing.is_set)
            removed = app._playlist._preparer.pending_event(article_ids[2])  # type: ignore[union-attr]

            app._playlist.remove(article_ids[2])

            assert removed is not None and removed.is_set()
            assert app._playlist.preparing_count == 2
            app._playlist.clear()
            assert app._playlist.preparing_count == 0
            engine.gate.set()
            await pilot.pause(0.05)
            assert engine.prepared_texts().count("BBC News. Article 1 of 3.") == 1
            assert "BBC News. Article 3 of 3." not in engine.prepared_texts()

    asyncio.run(runner())


def test_ui_playlist_prepares_restored_playlist_after_mount(app_config, tmp_path) -> None:
    app, _output, _engine = build_app(app_config, tmp_path)
    seed_articles(app, 2)

    async def first_run() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A")
            await pilot.press("q")

    asyncio.run(first_run())

    engine = FakePreparingTTSEngine()
    restarted, _output, _engine = build_app(app_config, tmp_path, engine=engine)

    async def second_run() -> None:
        async with restarted.run_test() as pilot:
            await wait_for(pilot, lambda: len(engine.prepared) == 2 and restarted._playlist.preparing_count == 0)

            assert ("Summary for Title 2.", "ru") in engine.prepared[1]

    asyncio.run(second_run())
