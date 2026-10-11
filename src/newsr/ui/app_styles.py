from __future__ import annotations

APP_CSS = """
Screen {
    background: $background;
    color: $foreground;
}
#chrome {
    height: 1fr;
}
#article-header {
    border: heavy $primary;
    background: $background;
    color: $primary;
    padding: 0 1;
    margin: 0;
    border-title-align: left;
}
#article-frame {
    height: 1fr;
    border: heavy $primary;
    background: $background;
}
#provider-home-table {
    height: 1fr;
    background: $background;
    color: $foreground;
    overflow-y: scroll;
    overflow-x: auto;
    scrollbar-size-vertical: 1;
    scrollbar-size-horizontal: 1;
    scrollbar-background: $panel;
    scrollbar-background-hover: $panel;
    scrollbar-background-active: $panel;
    scrollbar-color: $accent;
    scrollbar-color-hover: $primary;
    scrollbar-color-active: $primary;
    scrollbar-gutter: stable;
    scrollbar-visibility: visible;
}
#provider-home-empty {
    height: 1fr;
    content-align: center middle;
    color: $secondary;
    background: $background;
}
#article-pane {
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
#article-body {
    padding: 0 2 1 2;
    color: $foreground;
}
#article-url {
    dock: bottom;
    height: 1;
    padding: 0 1;
    color: $secondary;
    background: $panel;
}
#status {
    width: 1fr;
    color: $success;
    padding: 0;
}
#status-bar {
    height: 1;
    padding: 0 1;
}
#status-indicator {
    width: 3;
    margin-right: 1;
    color: $accent;
    display: none;
}
#help-text {
    background: $surface;
    color: $foreground;
    border: solid $secondary;
    padding: 1 2;
    width: 60;
    height: auto;
    margin: 4 8;
}
"""
