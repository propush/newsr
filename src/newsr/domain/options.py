from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AppOptions:
    theme_name: str | None = None
