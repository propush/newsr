from __future__ import annotations

import json
from collections.abc import Mapping
from time import perf_counter
from urllib.error import HTTPError

from ...cancellation import RefreshCancellation, cancellable_read
from ..transport import build_request, newsr_headers, open_request
from .base import LOGGER, TTSEngineError, configure_tts_logger

REQUEST_TIMEOUT_SECONDS = 120
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def post_for_bytes(
    url: str,
    payload: Mapping[str, object],
    *,
    engine: str,
    headers: Mapping[str, str],
    request_retries: int,
    cancellation: RefreshCancellation | None = None,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> bytes:
    configure_tts_logger()
    body = json.dumps(payload).encode("utf-8")
    request_headers = newsr_headers({"Content-Type": "application/json", **headers})
    max_attempts = request_retries + 1
    started_at = perf_counter()
    text_chars = len(str(payload.get("input") or payload.get("text") or ""))
    LOGGER.info("request_start engine=%s url=%s text_chars=%s", engine, url, text_chars)
    for attempt in range(1, max_attempts + 1):
        request = build_request(url, headers=request_headers, data=body, method="POST")
        try:
            with open_request(request, cancellation, timeout=timeout) as response:
                data = cancellable_read(response, cancellation)
        except HTTPError as exc:
            detail = _error_detail(exc)
            if exc.code in _RETRYABLE_STATUSES and attempt < max_attempts:
                _log_retry(engine, attempt, max_attempts, exc)
                continue
            LOGGER.error("request_failed engine=%s status=%s detail=%s", engine, exc.code, detail)
            raise TTSEngineError(f"{engine} returned HTTP {exc.code}: {detail}") from exc
        except OSError as exc:
            if cancellation is not None:
                cancellation.raise_if_cancelled()
            if attempt < max_attempts:
                _log_retry(engine, attempt, max_attempts, exc)
                continue
            LOGGER.error("request_failed engine=%s error_type=%s error=%s", engine, type(exc).__name__, exc)
            raise TTSEngineError(f"{engine} request failed: {exc}") from exc
        LOGGER.info(
            "request_done engine=%s bytes=%s elapsed=%.2fs",
            engine,
            len(data),
            perf_counter() - started_at,
        )
        return data
    raise TTSEngineError(f"{engine} request failed")


def _error_detail(exc: HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        raw = ""
    return raw[:300] or str(exc.reason)


def _log_retry(engine: str, attempt: int, max_attempts: int, exc: Exception) -> None:
    LOGGER.warning(
        "request_retry engine=%s attempt=%s max_attempts=%s error_type=%s error=%s",
        engine,
        attempt,
        max_attempts,
        type(exc).__name__,
        exc,
    )
