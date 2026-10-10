from __future__ import annotations

from dataclasses import replace

import pytest

from newsr.domain import ProviderTarget


def test_catalog_replacement_preserves_retained_selections_and_updates_metadata(storage) -> None:
    world, technology = storage.list_provider_targets("bbc")
    new_target = ProviderTarget("bbc", "arts", "category", "Arts", {"path": "/arts"}, selected=True)
    updated = replace(technology, label="Technology", payload={"path": "/technology"})

    storage.replace_provider_targets("bbc", [updated, new_target])

    targets = storage.list_provider_targets("bbc")
    assert [target.target_key for target in targets] == ["technology", "arts"]
    assert targets[0].payload == {"path": "/technology"}
    assert targets[0].selected is True
    assert targets[1].selected is False
    assert [target.target_key for target in storage.list_selected_targets("bbc")] == ["technology"]


def test_catalog_replacement_preserves_empty_selection_and_is_repeatable(storage) -> None:
    targets = storage.list_provider_targets("bbc")
    storage.set_selected_targets("bbc", [])

    storage.replace_provider_targets("bbc", targets)
    storage.replace_provider_targets("bbc", targets)

    assert storage.list_selected_targets("bbc") == []
    assert [target.target_key for target in storage.list_provider_targets("bbc")] == ["world", "technology"]


def test_catalog_replacement_rolls_back_metadata_and_selection_on_failure(storage) -> None:
    targets = storage.list_provider_targets("bbc")
    updated = replace(targets[0], label="Updated")
    invalid = ProviderTarget("bbc", "invalid", "category", "Invalid", {"path": object()})

    with pytest.raises(TypeError):
        storage.replace_provider_targets("bbc", [updated, invalid])

    assert storage.list_provider_targets("bbc") == targets
    assert {target.target_key for target in storage.list_selected_targets("bbc")} == {"world", "technology"}


def test_empty_catalog_removes_targets_and_their_selection_rows(storage) -> None:
    storage.replace_provider_targets("bbc", [])

    assert storage.list_provider_targets("bbc") == []
    assert storage.list_selected_targets("bbc") == []
