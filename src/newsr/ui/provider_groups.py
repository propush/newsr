from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Literal, TypeVar

from ..ui_text import UILocalizer

ProviderGroupId = Literal["virtual", "providers", "topics"]

T = TypeVar("T")

PROVIDER_GROUP_ORDER: tuple[ProviderGroupId, ...] = ("virtual", "providers", "topics")


@dataclass(slots=True)
class ProviderGroup(Generic[T]):
    group_id: ProviderGroupId
    items: list[T]


def provider_group_id_for_type(provider_type: str) -> ProviderGroupId | None:
    if provider_type == "all":
        return "virtual"
    if provider_type == "http":
        return "providers"
    if provider_type == "topic":
        return "topics"
    return None


def provider_group_label(ui: UILocalizer, group_id: ProviderGroupId) -> str:
    return ui.text(f"provider_group.{group_id}")


def build_provider_groups(
    items: Iterable[T],
    *,
    group_for_item: Callable[[T], ProviderGroupId | None],
    sort_items: Callable[[list[T]], list[T]],
    group_order: tuple[ProviderGroupId, ...] = PROVIDER_GROUP_ORDER,
) -> list[ProviderGroup[T]]:
    grouped_items: dict[ProviderGroupId, list[T]] = {group_id: [] for group_id in group_order}
    for item in items:
        group_id = group_for_item(item)
        if group_id is None or group_id not in grouped_items:
            continue
        grouped_items[group_id].append(item)

    result: list[ProviderGroup[T]] = []
    for group_id in group_order:
        group_items = grouped_items[group_id]
        if not group_items:
            continue
        result.append(ProviderGroup(group_id=group_id, items=sort_items(group_items)))
    return result
