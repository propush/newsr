from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ViewMode(StrEnum):
    FULL = "full"
    SUMMARY = "summary"


@dataclass(slots=True)
class ReaderState:
    article_id: str | None
    view_mode: ViewMode
    scroll_offset: int
