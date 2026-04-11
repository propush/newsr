from __future__ import annotations

from datetime import datetime


def parse_published_time(raw: str | None) -> datetime | None:
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        return None
