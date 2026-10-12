from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaylistItem:
    article_id: str
    scope_id: str
