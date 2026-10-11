from __future__ import annotations

from textual.widgets import Footer, Markdown, Static

from newsr.ui import NewsReaderApp


def body_source(app: NewsReaderApp) -> str:
    return app.query_one("#article-body", Markdown).source


def article_pane(app: NewsReaderApp):
    return app.query_one("#article-pane")


def url_source(app: NewsReaderApp) -> str:
    return app.query_one("#article-url", Static).content


def plain_content(value) -> str:  # type: ignore[no-untyped-def]
    return value.plain if hasattr(value, "plain") else str(value)


def header_text(app: NewsReaderApp) -> str:
    return plain_content(app.query_one("#article-header", Static).content)


def footer_bindings(app: NewsReaderApp) -> list[tuple[str, str, str]]:
    footer = app.query_one(Footer)
    return [(child.key_display, child.description, child.action) for child in footer.children]
