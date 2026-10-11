from __future__ import annotations

import logging

from ..cancellation import RefreshCancellation
from .models import BriefProgress, ProgressCallback
from .repair import BriefValidation

LOGGER = logging.getLogger("newsr.llm")


def emit_progress(
    callback: ProgressCallback | None,
    completed: int,
    progress_total: int,
    message_key: str,
    **message_args: object,
) -> None:
    LOGGER.info(
        "brief_progress completed=%s total=%s message_key=%r message_args=%r",
        completed,
        max(1, progress_total),
        message_key,
        message_args,
    )
    if callback is not None:
        callback(
            BriefProgress(
                completed=completed,
                total=max(1, progress_total),
                message_key=message_key,
                message_args=dict(message_args),
            )
        )


def raise_if_cancelled(cancellation: RefreshCancellation | None) -> None:
    if cancellation is not None:
        cancellation.raise_if_cancelled()


def log_validation(
    stage: str,
    validation: BriefValidation,
    *,
    attempt: int | None = None,
    batch_index: int | None = None,
    batch_count: int | None = None,
) -> None:
    LOGGER.warning(
        "brief_validation_failed stage=%s attempt=%s batch=%s batches=%s invalid=%s missing=%s unreferenced=%s",
        stage,
        attempt,
        batch_index,
        batch_count,
        len(validation.invalid_numbers),
        len(validation.missing_numbers),
        len(validation.unreferenced_lines),
    )
