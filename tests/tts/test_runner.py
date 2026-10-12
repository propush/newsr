from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from time import sleep

from newsr.domain import ViewMode
from newsr.tts.runner import PlannedItem, PlaybackRunner
from newsr.tts.script import SpeechSegment

from tests.tts.fakes import FakeAudioOutput, FakeTTSEngine


def planned(article_id: str, *texts: str) -> PlannedItem:
    return PlannedItem(
        article_id=article_id,
        scope_id="[ALL]",
        mode=ViewMode.FULL,
        segments=tuple(SpeechSegment(text, "en") for text in texts),
    )


class FakeHost:
    def __init__(self, items: list[PlannedItem]) -> None:
        self.queue = list(items)
        self.events: list[tuple[str, object]] = []
        self._lock = Lock()

    def start_next_item(self, runner: PlaybackRunner) -> PlannedItem | None:
        with self._lock:
            item = self.queue[0] if self.queue else None
            self.events.append(("started", item.article_id if item else None))
            return item

    def peek_next_item(self, runner: PlaybackRunner, after_article_id: str) -> PlannedItem | None:
        with self._lock:
            ids = [item.article_id for item in self.queue]
            if after_article_id not in ids:
                return None
            index = ids.index(after_article_id) + 1
            return self.queue[index] if index < len(self.queue) else None

    def item_finished(self, runner: PlaybackRunner, article_id: str) -> None:
        with self._lock:
            self.queue = [item for item in self.queue if item.article_id != article_id]
            self.events.append(("finished", article_id))

    def buffering_changed(self, runner: PlaybackRunner, buffering: bool) -> None:
        self.events.append(("buffering", buffering))

    def playback_failed(self, runner: PlaybackRunner, article_id: str | None, message: str) -> None:
        self.events.append(("failed", (article_id, message)))

    def playback_finished(self, runner: PlaybackRunner) -> None:
        self.events.append(("done", None))


def direct_dispatch(callback: Callable[..., object], *args: object) -> object:
    return callback(*args)


def make_runner(host: FakeHost, engine: FakeTTSEngine, output: FakeAudioOutput) -> PlaybackRunner:
    return PlaybackRunner(host=host, engine_provider=lambda: engine, output=output, dispatch=direct_dispatch)


def wait_until(predicate: Callable[[], bool]) -> None:
    for _ in range(500):
        if predicate():
            return
        sleep(0.01)
    raise AssertionError("condition was not reached")


def test_runner_plays_items_in_order_and_reports_completion() -> None:
    host = FakeHost([planned("a", "A intro", "A body"), planned("b", "B intro")])
    engine = FakeTTSEngine()
    output = FakeAudioOutput()
    runner = make_runner(host, engine, output)

    runner.start()
    runner.join(5)

    assert output.played == ["A intro", "A body", "B intro"]
    assert [event for event in host.events if event[0] in {"finished", "done"}] == [
        ("finished", "a"),
        ("finished", "b"),
        ("done", None),
    ]
    assert host.queue == []


def test_runner_prefetches_three_segments_ahead_across_items() -> None:
    host = FakeHost(
        [planned("a", "A intro", "A title"), planned("b", "B intro", "B title", "B body 1", "B body 2")]
    )
    engine = FakeTTSEngine()
    output = FakeAudioOutput(auto_finish=False)
    runner = make_runner(host, engine, output)

    runner.start()
    wait_until(lambda: output.played == ["A intro"])
    wait_until(lambda: len(engine.calls) == 4)
    assert [text for text, _language in engine.calls] == ["A intro", "A title", "B intro", "B title"]

    output.release()
    wait_until(lambda: len(engine.calls) == 5)
    assert engine.calls[-1][0] == "B body 1"
    runner.stop()
    runner.join(5)


def test_runner_skip_and_restart_interrupt_the_current_item() -> None:
    host = FakeHost([planned("a", "A intro", "A body"), planned("b", "B intro")])
    engine = FakeTTSEngine()
    output = FakeAudioOutput(auto_finish=False)
    runner = make_runner(host, engine, output)

    runner.start()
    wait_until(lambda: output.played == ["A intro"])
    output.release()
    wait_until(lambda: output.played == ["A intro", "A body"])

    runner.restart_item()
    wait_until(lambda: output.played[-1:] == ["A intro"] and len(output.played) == 3)
    assert ("finished", "a") not in host.events

    runner.skip()
    wait_until(lambda: output.played[-1:] == ["B intro"])
    assert ("finished", "a") in host.events
    runner.stop()
    runner.join(5)
    assert ("finished", "b") not in host.events


def test_runner_reports_synthesis_errors_and_stops() -> None:
    host = FakeHost([planned("a", "A intro", "broken body"), planned("b", "B intro")])
    engine = FakeTTSEngine(fail_on="broken")
    output = FakeAudioOutput()
    runner = make_runner(host, engine, output)

    runner.start()
    runner.join(5)

    assert output.played == ["A intro"]
    assert ("failed", ("a", "cannot speak broken")) in host.events
    assert ("finished", "a") not in host.events
    assert runner.is_cancelled


def test_runner_stop_cancels_blocked_playback() -> None:
    host = FakeHost([planned("a", "A intro")])
    output = FakeAudioOutput(auto_finish=False)
    runner = make_runner(host, FakeTTSEngine(), output)

    runner.start()
    wait_until(lambda: output.played == ["A intro"])
    runner.stop()
    runner.join(5)

    assert ("finished", "a") not in host.events
    assert ("done", None) not in host.events


def test_runner_reports_engine_construction_errors() -> None:
    host = FakeHost([planned("a", "A intro")])

    def broken_engine() -> FakeTTSEngine:
        raise RuntimeError("engine unavailable")

    runner = PlaybackRunner(
        host=host,
        engine_provider=broken_engine,
        output=FakeAudioOutput(),
        dispatch=direct_dispatch,
    )
    runner.start()
    runner.join(5)

    assert host.events == [("failed", (None, "engine unavailable"))]
