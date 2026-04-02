from __future__ import annotations

from rich.text import Text


GROUP_HEADER_STYLE = "dim italic $secondary"


def group_header_text(label: str) -> Text:
    return Text(label, style=GROUP_HEADER_STYLE, justify="center")


def framed_group_header_text(label: str, width: int) -> Text:
    padded_label = f" {label} "
    if width <= len(padded_label):
        return Text(label, style=GROUP_HEADER_STYLE, justify="center")
    return Text(padded_label.center(width, "─"), style=GROUP_HEADER_STYLE, justify="center")
