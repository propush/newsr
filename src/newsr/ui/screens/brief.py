from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding, BindingsMap
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Markdown, ProgressBar, RadioButton, RadioSet, Static

from ...brief import BriefOptions, BriefPeriod, BriefProgress
from ...ui_text import UILocalizer


class BriefScreen(ModalScreen[None]):
    CSS = """
    BriefScreen {
        background: transparent;
    }
    #brief-shell {
        width: 82;
        height: 1fr;
        margin: 1 4;
        border: heavy $primary;
        background: $background;
    }
    #brief-header {
        height: auto;
        padding: 0 1;
        color: $primary;
        background: $panel;
        border-bottom: solid $primary;
    }
    #brief-controls {
        height: auto;
        padding: 1 2 0 2;
    }
    #brief-period {
        height: auto;
        margin-bottom: 1;
    }
    #brief-options {
        height: auto;
        margin-bottom: 1;
    }
    #brief-buttons {
        height: auto;
        margin-bottom: 1;
    }
    #brief-buttons Button {
        width: 1fr;
    }
    #brief-progress {
        height: 1;
        display: none;
    }
    #brief-body-pane {
        height: 1fr;
        overflow-y: scroll;
        scrollbar-size-vertical: 1;
        scrollbar-background: $panel;
        scrollbar-background-hover: $panel;
        scrollbar-background-active: $panel;
        scrollbar-color: $accent;
        scrollbar-color-hover: $primary;
        scrollbar-color-active: $primary;
        scrollbar-gutter: stable;
        scrollbar-visibility: visible;
    }
    #brief-body {
        padding: 0 2 1 2;
        color: $foreground;
    }
    #brief-hint {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $secondary;
        background: $panel;
    }
    """

    BINDINGS = []

    _FOCUS_ORDER = (
        "brief-period",
        "brief-include-topics",
        "brief-mark-read",
        "brief-generate",
        "brief-cancel",
    )

    def __init__(self, ui: UILocalizer) -> None:
        super().__init__()
        self._ui = ui
        self._bindings = BindingsMap(self._build_bindings())
        self.period = BriefPeriod.LAST_24H
        self.include_topics = False
        self.mark_read = True
        self.generating = False

    def _build_bindings(self) -> list[Binding | tuple[str, str, str]]:
        return [
            ("escape", "close_overlay", self._ui.text("brief.binding.close")),
            Binding("g", "generate", self._ui.text("brief.binding.generate"), show=False),
            Binding("tab", "focus_next", show=False),
            Binding("shift+tab", "focus_previous", show=False),
            Binding("up", "focus_previous", show=False),
            Binding("down", "focus_next", show=False),
            Binding("pageup,b", "page_up_report", show=False),
            Binding("pagedown,space", "page_down_report", show=False),
        ]

    def compose(self) -> ComposeResult:
        with Vertical(id="brief-shell"):
            yield Static(self._ui.text("brief.header"), id="brief-header")
            with Vertical(id="brief-controls"):
                yield Static(self._ui.text("brief.period.label"))
                with RadioSet(id="brief-period"):
                    yield RadioButton(self._ui.text("brief.period.last_24h"), value=True, id="brief-period-24h")
                    yield RadioButton(self._ui.text("brief.period.last_week"), id="brief-period-week")
                    yield RadioButton(self._ui.text("brief.period.all_unread"), id="brief-period-unread")
                with Vertical(id="brief-options"):
                    yield Checkbox(
                        self._ui.text("brief.option.include_topics"),
                        value=False,
                        id="brief-include-topics",
                    )
                    yield Checkbox(
                        self._ui.text("brief.option.mark_read"),
                        value=True,
                        id="brief-mark-read",
                    )
                with Horizontal(id="brief-buttons"):
                    yield Button(self._ui.text("brief.button.generate"), variant="primary", id="brief-generate")
                    yield Button(self._ui.text("brief.button.cancel"), id="brief-cancel")
                yield ProgressBar(total=100, show_eta=False, id="brief-progress")
            with VerticalScroll(id="brief-body-pane", can_focus=False):
                yield Markdown(self._ui.text("brief.body.ready"), id="brief-body")
            yield Static(self._ui.text("brief.hint"), id="brief-hint")

    def on_mount(self) -> None:
        self.query_one("#brief-period", RadioSet).focus()

    def current_options(self) -> BriefOptions:
        return BriefOptions(
            period=self.period,
            include_topics=self.include_topics,
            mark_read=self.mark_read,
        )

    def set_generating(self, value: bool) -> None:
        self.generating = value
        for control_id in self._FOCUS_ORDER[:-1]:
            try:
                self.query_one(f"#{control_id}").disabled = value
            except NoMatches:
                continue
        try:
            progress = self.query_one("#brief-progress", ProgressBar)
            progress.display = value
            if value:
                progress.update(total=100, progress=0)
        except NoMatches:
            pass

    def set_progress(self, progress_value: BriefProgress) -> None:
        try:
            progress = self.query_one("#brief-progress", ProgressBar)
            percent = min(99, int((progress_value.completed / progress_value.total) * 100))
            progress.update(total=100, progress=percent)
        except NoMatches:
            pass
        self.set_content(
            self._ui.text("brief.body.generating", status=self._ui.status(progress_value.status))
        )

    def set_report(self, report: str) -> None:
        self.set_generating(False)
        try:
            self.query_one("#brief-progress", ProgressBar).update(total=100, progress=100)
        except NoMatches:
            pass
        self.set_content(report)

    def set_error(self, error: str) -> None:
        self.set_generating(False)
        self.set_content(self._ui.text("brief.body.failed", error=error))

    def set_content(self, value: str) -> None:
        try:
            self.query_one("#brief-body", Markdown).update(value)
            self.query_one("#brief-body-pane", VerticalScroll).scroll_to(y=0, animate=False)
        except NoMatches:
            return

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id != "brief-period":
            return
        period_by_id = {
            "brief-period-24h": BriefPeriod.LAST_24H,
            "brief-period-week": BriefPeriod.LAST_WEEK,
            "brief-period-unread": BriefPeriod.ALL_UNREAD,
        }
        self.period = period_by_id.get(event.pressed.id or "", self.period)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "brief-include-topics":
            self.include_topics = event.value
        if event.checkbox.id == "brief-mark-read":
            self.mark_read = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "brief-generate":
            self.app.generate_brief()
            return
        self.app.close_brief()

    def action_generate(self) -> None:
        self.app.generate_brief()

    def action_close_overlay(self) -> None:
        self.app.close_brief()

    def action_focus_previous(self) -> None:
        self._move_focus(-1)

    def action_focus_next(self) -> None:
        self._move_focus(1)

    def action_page_up_report(self) -> None:
        self.query_one("#brief-body-pane", VerticalScroll).scroll_page_up(animate=False)

    def action_page_down_report(self) -> None:
        self.query_one("#brief-body-pane", VerticalScroll).scroll_page_down(animate=False)

    def _move_focus(self, delta: int) -> None:
        focused_id = self._focus_group_id(getattr(self.app.focused, "id", None))
        if focused_id not in self._FOCUS_ORDER:
            target_index = 0
        else:
            target_index = (self._FOCUS_ORDER.index(focused_id) + delta) % len(self._FOCUS_ORDER)
        for offset in range(len(self._FOCUS_ORDER)):
            target_id = self._FOCUS_ORDER[(target_index + (offset * delta)) % len(self._FOCUS_ORDER)]
            try:
                target = self.query_one(f"#{target_id}")
            except NoMatches:
                continue
            if not getattr(target, "disabled", False):
                target.focus()
                return

    @staticmethod
    def _focus_group_id(focused_id: str | None) -> str | None:
        if focused_id in {"brief-period-24h", "brief-period-week", "brief-period-unread"}:
            return "brief-period"
        return focused_id
