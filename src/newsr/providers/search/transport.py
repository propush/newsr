from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Mapping, Protocol

from curl_cffi import requests as curl_requests

from ...cancellation import RefreshCancellation, resolve_request_timeout

IMPERSONATE_TARGETS = ("chrome", "safari", "firefox")


@dataclass(slots=True)
class SearchResponse:
    status: int
    text: str


class SearchTransport(Protocol):
    def post(
        self,
        url: str,
        form: Mapping[str, str],
        *,
        headers: Mapping[str, str],
        cancellation: RefreshCancellation | None = None,
        timeout: float = 30,
    ) -> SearchResponse: ...

    def reset(self) -> None: ...


class CurlBrowserTransport:
    """Browser-impersonating HTTP session shared by all search requests."""

    def __init__(
        self,
        impersonate_targets: tuple[str, ...] = IMPERSONATE_TARGETS,
        *,
        session_factory: Callable[[str], Any] | None = None,
    ) -> None:
        if not impersonate_targets:
            raise ValueError("impersonate_targets must not be empty")
        self._targets = impersonate_targets
        self._target_index = 0
        self._session_factory = session_factory or _new_session
        self._session: Any | None = None
        self._lock = Lock()

    @property
    def impersonate(self) -> str:
        return self._targets[self._target_index]

    def post(
        self,
        url: str,
        form: Mapping[str, str],
        *,
        headers: Mapping[str, str],
        cancellation: RefreshCancellation | None = None,
        timeout: float = 30,
    ) -> SearchResponse:
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        with self._lock:
            if self._session is None:
                self._session = self._session_factory(self.impersonate)
            response = self._session.post(
                url,
                data=dict(form),
                headers=dict(headers),
                timeout=resolve_request_timeout(cancellation, timeout),
            )
            result = SearchResponse(status=response.status_code, text=response.text)
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        return result

    def reset(self) -> None:
        with self._lock:
            session = self._session
            self._session = None
            self._target_index = (self._target_index + 1) % len(self._targets)
        if session is not None:
            session.close()


def _new_session(impersonate: str) -> Any:
    return curl_requests.Session(impersonate=impersonate)
