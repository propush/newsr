from __future__ import annotations

from textual.content import Content, Span

from newsr.ui.screens.brief_reader import _style_article_references
from newsr.ui.themes import BRIEF_ARTICLE_REFERENCE_COLOR, OLD_FIDO_THEME


def test_old_fido_uses_dedicated_brief_article_reference_color() -> None:
    styled = _style_article_references(Content("Short extract [1]."))

    assert OLD_FIDO_THEME.accent == "#c8c8c8"
    assert OLD_FIDO_THEME.variables[BRIEF_ARTICLE_REFERENCE_COLOR] == "#d8c24a"
    assert styled.spans == [
        Span(14, 17, style=f"${BRIEF_ARTICLE_REFERENCE_COLOR} bold")
    ]


def test_brief_article_reference_styling_leaves_surrounding_text_unchanged() -> None:
    existing = Span(0, 5, style="italic")

    styled = _style_article_references(Content("Short [12].", spans=[existing]))

    assert styled.plain == "Short [12]."
    assert styled.spans == [
        existing,
        Span(6, 10, style=f"${BRIEF_ARTICLE_REFERENCE_COLOR} bold"),
    ]
