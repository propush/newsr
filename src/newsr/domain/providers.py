from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


ProviderType = Literal["all", "http", "topic"]


@dataclass(slots=True)
class ProviderRecord:
    provider_id: str
    display_name: str
    enabled: bool
    provider_type: ProviderType = "http"
    update_schedule: str | None = None
    last_refresh_started_at: datetime | None = None
    last_refresh_completed_at: datetime | None = None
    settings: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ProviderTarget:
    provider_id: str
    target_key: str
    target_kind: str
    label: str
    payload: dict[str, str] = field(default_factory=dict)
    discovered_at: datetime | None = None
    selected: bool = False
