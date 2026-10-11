from __future__ import annotations

from textual.widgets import DataTable

from newsr.ui import CategorySelectionScreen, NewsReaderApp


def category_screen(app: NewsReaderApp) -> CategorySelectionScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, CategorySelectionScreen):
            return screen
    return None


def provider_list(app: NewsReaderApp) -> DataTable:
    screen = category_screen(app)
    assert screen is not None
    return screen.query_one("#provider-list", DataTable)


def provider_rows(app: NewsReaderApp) -> list[list[str]]:
    table = provider_list(app)
    rows: list[list[str]] = []
    for row_index in range(table.row_count):
        row = table.get_row_at(row_index)
        rows.append([str(cell) for cell in row])
    return rows


def provider_row_index(app: NewsReaderApp, display_name: str) -> int:
    for row_index, row in enumerate(provider_rows(app)):
        if len(row) > 1 and row[1] == display_name:
            return row_index
    raise AssertionError(f"provider row not found for {display_name}")


def target_list(app: NewsReaderApp) -> DataTable:
    screen = category_screen(app)
    assert screen is not None
    return screen.query_one("#target-list", DataTable)


async def wait_for_source_manager(app: NewsReaderApp, pilot) -> CategorySelectionScreen:  # type: ignore[no-untyped-def]
    for _ in range(20):
        await pilot.pause()
        screen = category_screen(app)
        if screen is not None and provider_list(app).row_count and target_list(app).row_count:
            return screen
    raise AssertionError("source manager did not finish loading")
