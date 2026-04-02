from __future__ import annotations

from datetime import UTC, datetime

import pytest

from newsr.scheduling import is_due_on_schedule, validate_cron_expression


def test_validate_cron_expression_normalizes_spacing() -> None:
    assert validate_cron_expression("  */15   * * * *  ") == "*/15 * * * *"


def test_validate_cron_expression_rejects_invalid_field_count() -> None:
    with pytest.raises(ValueError, match="5 fields"):
        validate_cron_expression("* * * *")


def test_is_due_on_schedule_returns_true_when_never_completed() -> None:
    assert is_due_on_schedule("0 * * * *", last_completed_at=None) is True


def test_is_due_on_schedule_checks_for_matching_minute_since_last_completion() -> None:
    now = datetime(2026, 4, 2, 12, 30, tzinfo=UTC)
    assert is_due_on_schedule(
        "*/15 * * * *",
        last_completed_at=datetime(2026, 4, 2, 12, 14, tzinfo=UTC),
        now=now,
    ) is True
    assert is_due_on_schedule(
        "*/15 * * * *",
        last_completed_at=datetime(2026, 4, 2, 12, 30, tzinfo=UTC),
        now=now,
    ) is False
