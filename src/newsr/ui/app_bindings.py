from __future__ import annotations

from textual.binding import Binding

from ..ui_text import UILocalizer


def build_app_bindings(
    ui: UILocalizer,
    *,
    provider_home_open: bool = False,
) -> list[Binding | tuple[str, str, str]]:
    return [
        Binding("ctrl+c,super+c,ctrl+shift+c", "copy_selection", show=False, priority=True),
        Binding("left", "previous_article", ui.text("app.binding.previous"), show=False),
        Binding("right", "next_article", ui.text("app.binding.next"), show=False),
        Binding("up", "scroll_up", ui.text("app.binding.up"), show=False),
        Binding("down", "scroll_down", ui.text("app.binding.down"), show=False),
        Binding("pageup", "page_up", ui.text("app.binding.pgup"), show=False),
        Binding("pagedown", "page_down", ui.text("app.binding.pgdn"), show=False),
        Binding("b", "brief_or_page_up", ui.text("app.binding.brief"), show=provider_home_open),
        ("k", "classify_article_categories", ui.text("app.binding.classify")),
        Binding("space", "space_down", ui.text("app.binding.space"), show=False),
        ("s", "cycle_view_mode", ui.text("app.binding.mode")),
        ("m", "show_or_refresh_more_info", ui.text("app.binding.more_info")),
        Binding("?", "show_article_qa", ui.text("app.binding.ask")),
        ("l", "show_quick_nav", ui.text("app.binding.list")),
        Binding("a", "playlist_add_current", ui.text("app.binding.playlist_add"), show=False),
        Binding("A", "playlist_add_rest", ui.text("app.binding.playlist_add_rest"), show=False),
        Binding("p", "toggle_playback", ui.text("app.binding.play_pause"), show=False),
        ("P", "show_playlist", ui.text("app.binding.playlist")),
        Binding("right_square_bracket", "playlist_skip", ui.text("app.binding.playlist_skip"), show=False),
        Binding("left_square_bracket", "playlist_previous", ui.text("app.binding.playlist_previous"), show=False),
        Binding("full_stop", "playlist_seek_forward", ui.text("app.binding.playlist_seek_forward"), show=False),
        Binding("comma", "playlist_seek_back", ui.text("app.binding.playlist_seek_back"), show=False),
        ("c", "show_source_manager", ui.text("app.binding.sources")),
        ("e", "export_current", ui.text("app.binding.export")),
        ("o", "open_article", ui.text("app.binding.open")),
        ("w", "watch_topic", ui.text("app.binding.watch_topic")),
        ("d", "download_articles", ui.text("app.binding.download")),
        ("h", "show_help", ui.text("app.binding.help")),
        Binding("ctrl+p", "command_palette", show=False),
        Binding("escape", "return_to_provider_home", ui.text("app.binding.providers"), show=False),
        ("q", "quit_reader", ui.text("app.binding.quit")),
    ]
