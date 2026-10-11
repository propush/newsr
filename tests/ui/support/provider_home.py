from __future__ import annotations

from rich.text import Text
from textual.widgets import DataTable

from newsr.ui import NewsReaderApp


def provider_home_screen(app: NewsReaderApp):
    return app if app.provider_home_open else None


def provider_home_table(app: NewsReaderApp) -> DataTable:
    assert app.provider_home_open
    return app.query_one("#provider-home-table", DataTable)


def provider_home_rows(app: NewsReaderApp) -> list[list[str]]:
    table = provider_home_table(app)
    rows: list[list[str]] = []
    for row_index in range(table.row_count):
        row = table.get_row_at(row_index)
        rows.append([str(cell).strip() for cell in row])
    return rows


def assert_framed_provider_home_header(value: object, label: str) -> None:
    rendered = value.plain if isinstance(value, Text) else str(value)
    assert rendered.startswith("─")
    assert rendered.endswith("─")
    assert f" {label} " in rendered
    assert rendered != label
    if isinstance(value, Text):
        assert value.justify == "center"
        assert value.style == "dim italic $secondary"


def provider_home_row_index(app: NewsReaderApp, display_name: str) -> int:
    for row_index, row in enumerate(provider_home_rows(app)):
        if row[0] == display_name:
            return row_index
    raise AssertionError(f"provider home row not found for {display_name}")
