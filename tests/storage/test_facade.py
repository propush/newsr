from __future__ import annotations

from newsr.domain import AppOptions, ReaderState, ViewMode


def test_storage_persists_reader_state(storage) -> None:
    all_state = ReaderState(
        article_id="test-1",
        view_mode=ViewMode.SUMMARY,
        scroll_offset=12,
    )
    provider_state = ReaderState(
        article_id="bbc:test-2",
        view_mode=ViewMode.ORIGINAL,
        scroll_offset=3,
    )

    storage.save_reader_state("[ALL]", all_state)
    storage.save_reader_state("bbc", provider_state)

    assert storage.load_reader_state("[ALL]") == all_state
    assert storage.load_reader_state("bbc") == provider_state


def test_storage_persists_options(storage) -> None:
    options = AppOptions(theme_name="gruvbox")

    storage.save_options(options)

    assert storage.load_options() == options
