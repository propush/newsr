from __future__ import annotations

import logging
from pathlib import Path


_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def configure_cache_logger(logger: logging.Logger, *, filename: str) -> None:
    if logger.handlers:
        return
    log_path = Path.cwd() / "cache" / filename
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
