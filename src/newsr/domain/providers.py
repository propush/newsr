from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class ProviderRecord:
    provider_id: str
    display_name: str
    enabled: bool
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
