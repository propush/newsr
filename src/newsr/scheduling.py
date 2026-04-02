from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


DEFAULT_UPDATE_SCHEDULE = "0 * * * *"


@dataclass(frozen=True, slots=True)
class CronField:
    allowed: frozenset[int]
    unrestricted: bool


@dataclass(frozen=True, slots=True)
class CronExpression:
    minute: CronField
    hour: CronField
    day_of_month: CronField
    month: CronField
    day_of_week: CronField

    def matches(self, value: datetime) -> bool:
        minute = value.minute
        hour = value.hour
        day_of_month = value.day
        month = value.month
        day_of_week = (value.weekday() + 1) % 7
        if minute not in self.minute.allowed or hour not in self.hour.allowed:
            return False
        if month not in self.month.allowed:
            return False
        day_of_month_match = day_of_month in self.day_of_month.allowed
        day_of_week_match = day_of_week in self.day_of_week.allowed
        if self.day_of_month.unrestricted or self.day_of_week.unrestricted:
            return day_of_month_match and day_of_week_match
        return day_of_month_match or day_of_week_match


def normalize_cron_expression(value: str) -> str:
    return " ".join(value.strip().split())


def validate_cron_expression(value: str) -> str:
    normalized = normalize_cron_expression(value)
    parse_cron_expression(normalized)
    return normalized


def parse_cron_expression(value: str) -> CronExpression:
    normalized = normalize_cron_expression(value)
    fields = normalized.split(" ")
    if len(fields) != 5:
        raise ValueError("cron expression must have 5 fields")
    minute, hour, day_of_month, month, day_of_week = fields
    return CronExpression(
        minute=_parse_field(minute, 0, 59, "minute"),
        hour=_parse_field(hour, 0, 23, "hour"),
        day_of_month=_parse_field(day_of_month, 1, 31, "day of month"),
        month=_parse_field(month, 1, 12, "month"),
        day_of_week=_parse_field(day_of_week, 0, 7, "day of week", normalize_weekday=True),
    )


def is_due_on_schedule(
    expression: str,
    *,
    last_completed_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    if last_completed_at is None:
        return True
    current = _minute_floor(now or datetime.now(UTC))
    previous = _minute_floor(last_completed_at.astimezone(UTC))
    if previous >= current:
        return False
    cron = parse_cron_expression(expression)
    candidate = previous + timedelta(minutes=1)
    while candidate <= current:
        if cron.matches(candidate):
            return True
        candidate += timedelta(minutes=1)
    return False


def _minute_floor(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(second=0, microsecond=0)


def _parse_field(
    raw: str,
    minimum: int,
    maximum: int,
    label: str,
    *,
    normalize_weekday: bool = False,
) -> CronField:
    if not raw:
        raise ValueError(f"{label} field is empty")
    parts = raw.split(",")
    allowed: set[int] = set()
    unrestricted = raw == "*"
    for part in parts:
        allowed.update(
            _expand_part(
                part.strip(),
                minimum,
                maximum,
                label,
                normalize_weekday=normalize_weekday,
            )
        )
    if not allowed:
        raise ValueError(f"{label} field has no values")
    return CronField(allowed=frozenset(allowed), unrestricted=unrestricted)


def _expand_part(
    raw: str,
    minimum: int,
    maximum: int,
    label: str,
    *,
    normalize_weekday: bool = False,
) -> set[int]:
    if not raw:
        raise ValueError(f"{label} field contains an empty segment")
    if "/" in raw:
        base, step_text = raw.split("/", 1)
        step = _parse_number(step_text, minimum, maximum, label)
        if step <= 0:
            raise ValueError(f"{label} step must be positive")
        base_values = _expand_base(base or "*", minimum, maximum, label, normalize_weekday=normalize_weekday)
        ordered = sorted(base_values)
        start = ordered[0]
        return {value for value in ordered if (value - start) % step == 0}
    return _expand_base(raw, minimum, maximum, label, normalize_weekday=normalize_weekday)


def _expand_base(
    raw: str,
    minimum: int,
    maximum: int,
    label: str,
    *,
    normalize_weekday: bool = False,
) -> set[int]:
    if raw == "*":
        return {_normalize_weekday(value) if normalize_weekday else value for value in range(minimum, maximum + 1)}
    if "-" in raw:
        start_text, end_text = raw.split("-", 1)
        start = _parse_number(start_text, minimum, maximum, label)
        end = _parse_number(end_text, minimum, maximum, label)
        if start > end:
            raise ValueError(f"{label} range start must be <= end")
        values = range(start, end + 1)
        return {_normalize_weekday(value) if normalize_weekday else value for value in values}
    value = _parse_number(raw, minimum, maximum, label)
    return {_normalize_weekday(value) if normalize_weekday else value}


def _parse_number(raw: str, minimum: int, maximum: int, label: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{label} field contains an invalid number: {raw}") from exc
    if value < minimum or value > maximum:
        raise ValueError(f"{label} field must be between {minimum} and {maximum}")
    return value


def _normalize_weekday(value: int) -> int:
    return 0 if value == 7 else value
