from __future__ import annotations

from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown

from newsr.ui import (
    ArticleQuestionScreen,
    BriefReaderScreen,
    BriefScreen,
    ConfirmDialogScreen,
    ExportScreen,
    MoreInfoScreen,
    NewsReaderApp,
    OpenLinkConfirmScreen,
)


def article_qa_screen(app: NewsReaderApp) -> ArticleQuestionScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, ArticleQuestionScreen):
            return screen
    return None


def article_qa_body(app: NewsReaderApp) -> str:
    screen = article_qa_screen(app)
    assert screen is not None
    return screen.query_one("#article-qa-body", Markdown).source


def article_qa_input(app: NewsReaderApp) -> Input:
    screen = article_qa_screen(app)
    assert screen is not None
    return screen.query_one("#article-qa-input", Input)


def brief_screen(app: NewsReaderApp) -> BriefScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, BriefScreen):
            return screen
    return None


def brief_reader_screen(app: NewsReaderApp) -> BriefReaderScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, BriefReaderScreen):
            return screen
    return None


def brief_body(app: NewsReaderApp) -> str:
    screen = brief_screen(app)
    assert screen is not None
    return screen.query_one("#brief-body", Markdown).source


def brief_reader_body(app: NewsReaderApp) -> str:
    screen = brief_reader_screen(app)
    assert screen is not None
    return screen.query_one("#brief-reader-body", Markdown).source


def brief_reader_pane(app: NewsReaderApp) -> VerticalScroll:
    screen = brief_reader_screen(app)
    assert screen is not None
    return screen.query_one("#brief-reader-pane", VerticalScroll)


def open_link_confirm_screen(app: NewsReaderApp) -> OpenLinkConfirmScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, OpenLinkConfirmScreen):
            return screen
    return None


def confirm_dialog_screen(app: NewsReaderApp) -> ConfirmDialogScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, ConfirmDialogScreen):
            return screen
    return None


def export_screen(app: NewsReaderApp) -> ExportScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, ExportScreen):
            return screen
    return None


def more_info_screen(app: NewsReaderApp) -> MoreInfoScreen | None:
    for screen in reversed(app.screen_stack):
        if isinstance(screen, MoreInfoScreen):
            return screen
    return None


def more_info_body(app: NewsReaderApp) -> str:
    screen = more_info_screen(app)
    assert screen is not None
    return screen.query_one("#more-info-body", Markdown).source
