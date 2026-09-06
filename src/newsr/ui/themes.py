from __future__ import annotations

from textual.theme import Theme


BRIEF_ARTICLE_REFERENCE_COLOR = "brief-article-reference"


OLD_FIDO_THEME = Theme(
    name="old fido",
    primary="#d8c24a",
    secondary="#b0b0b0",
    success="#55ff55",
    accent="#c8c8c8",
    foreground="#d0d0d0",
    background="#000000",
    surface="#1f1f1f",
    panel="#101010",
    dark=True,
    variables={BRIEF_ARTICLE_REFERENCE_COLOR: "#d8c24a"},
)
