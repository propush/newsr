from __future__ import annotations

from collections.abc import Callable

from textual.widgets import Static

from newsr.ui import NewsReaderApp

from tests.tts.fakes import FakeAudioOutput, FakeTTSEngine
from tests.ui.support.app_state import disable_startup_refresh, seed_provider_article
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
