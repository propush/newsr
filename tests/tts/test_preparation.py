from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from time import sleep

import pytest

from newsr.providers.tts.base import LOGGER
from newsr.tts.preparation import SpeechPreparer

from tests.tts.fakes import FakePreparingTTSEngine


def texts(article_id: str, version: int = 1) -> list[tuple[str, str | None]]:
    return [(f"{article_id}{version}", "ru")]


def wait_until(predicate: Callable[[], bool]) -> None:
    for _ in range(500):
        if predicate():
            return
        sleep(0.01)
    raise AssertionError("condition was not reached")


@pytest.fixture
def tts_log() -> Iterator[list[str]]:
    messages: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(record.getMessage())

    handler = ListHandler()
    LOGGER.addHandler(handler)
    try:
        yield messages
    finally:
        LOGGER.removeHandler(handler)


def test_preparer_prepares_in_playlist_order_and_drops_removed_articles() -> None:
    engine = FakePreparingTTSEngine(blocked=True)
    changes: list[int] = []
    preparer = SpeechPreparer(engine, on_change=lambda: changes.append(preparer.pending_count))
    preparer.submit("a", texts("a"))
    assert engine.preparing.wait(5)
    for article_id in ("b", "c", "d"):
        preparer.submit(article_id, texts(article_id))
    dropped = preparer.pending_event("c")

    preparer.sync(["a", "d", "b"])

    assert dropped is not None and dropped.is_set()
    assert preparer.pending_event("c") is None
    assert preparer.pending_count == 3
    engine.gate.set()
    wait_until(lambda: preparer.pending_count == 0)
    assert engine.prepared_texts() == ["a1", "d1", "b1"]
    assert changes == [2, 1, 0]
    preparer.stop()


def test_preparer_keeps_one_event_while_jobs_are_replaced() -> None:
    engine = FakePreparingTTSEngine(blocked=True)
    preparer = SpeechPreparer(engine)
    preparer.submit("a", texts("a", 1))
    assert engine.preparing.wait(5)
    event = preparer.pending_event("a")
    preparer.submit("b", texts("b", 1))
    preparer.submit("b", texts("b", 2))
    preparer.submit("a", texts("a", 2))

    assert event is not None
    assert preparer.pending_event("a") is event
    engine.gate.set()
    assert event.wait(5)
    wait_until(lambda: preparer.pending_count == 0)
    assert engine.prepared_texts() == ["a1", "b2", "a2"]
    preparer.stop()


def test_preparer_logs_failures_and_releases_waiters(tts_log: list[str]) -> None:
    preparer = SpeechPreparer(FakePreparingTTSEngine(prepare_error=RuntimeError("LLM down")))
    preparer.submit("a", texts("a"))
    event = preparer.pending_event("a")

    assert event is not None and event.wait(5)
    wait_until(lambda: any("speech_prepare_failed article_id=a" in message for message in tts_log))
    assert preparer.pending_count == 0
    preparer.stop()


def test_preparer_cancels_the_running_job_when_its_article_leaves_the_playlist(tts_log: list[str]) -> None:
    engine = FakePreparingTTSEngine(blocked=True)
    preparer = SpeechPreparer(engine)
    preparer.submit("a", texts("a"))
    assert engine.preparing.wait(5)
    preparer.submit("b", texts("b"))
    waiting = preparer.pending_event("b")
    engine.preparing.clear()

    preparer.sync(["b"])

    assert engine.preparing.wait(5)
    assert engine.prepared_texts() == ["a1", "b1"]
    assert waiting is not None and not waiting.is_set()
    assert any("speech_prepare_dropped article_id=a" in message for message in tts_log)
    assert not any("speech_prepare_failed" in message for message in tts_log)
    engine.gate.set()
    assert waiting.wait(5)
    preparer.stop()


def test_preparer_stop_releases_every_waiter_and_ignores_new_jobs() -> None:
    engine = FakePreparingTTSEngine(blocked=True)
    preparer = SpeechPreparer(engine)
    preparer.submit("a", texts("a"))
    preparer.submit("b", texts("b"))
    assert engine.preparing.wait(5)
    events = [preparer.pending_event("a"), preparer.pending_event("b")]

    preparer.stop()
    preparer.stop()
    preparer.submit("c", texts("c"))

    assert all(event is not None and event.is_set() for event in events)
    assert preparer.pending_count == 0
    assert preparer.pending_event("c") is None
    sleep(0.05)
    assert engine.prepared_texts() == ["a1"]
