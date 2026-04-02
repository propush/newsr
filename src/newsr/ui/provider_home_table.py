from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.widgets import DataTable

if TYPE_CHECKING:
    from .app import NewsReaderApp


class ProviderHomeTable(DataTable):
    BINDINGS = [
        ("pageup", "provider_page_up", ""),
        ("pagedown", "provider_page_down", ""),
        ("home,ctrl+home", "provider_first", ""),
        ("end,ctrl+end", "provider_last", ""),
    ]

    @property
    def _newsr_app(self) -> NewsReaderApp:
        return cast("NewsReaderApp", self.app)

    def action_provider_page_up(self) -> None:
        self._newsr_app.page_provider_home(-1)

    def action_provider_page_down(self) -> None:
        self._newsr_app.page_provider_home(1)

    def action_provider_first(self) -> None:
        self._newsr_app.move_provider_home_to_boundary(first=True)

    def action_provider_last(self) -> None:
        self._newsr_app.move_provider_home_to_boundary(first=False)
