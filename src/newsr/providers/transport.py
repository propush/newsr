from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Mapping
from urllib.request import Request, urlopen

from ..cancellation import RefreshCancellation, cancellable_read, resolve_request_timeout

NEWSR_USER_AGENT = "newsr/0.1"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0 Safari/537.36 newsr/0.1"
)


def newsr_headers(headers: Mapping[str, str] | None = None) -> dict[str, str]:
    merged = {"User-Agent": NEWSR_USER_AGENT}
    if headers is not None:
        merged.update(headers)
    return merged


def browser_headers(headers: Mapping[str, str] | None = None) -> dict[str, str]:
    merged = {"User-Agent": BROWSER_USER_AGENT}
    if headers is not None:
        merged.update(headers)
    return merged


def build_request(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    data: bytes | None = None,
    method: str | None = None,
) -> Request:
    return Request(url, headers=dict(headers or {}), data=data, method=method)


@contextmanager
def open_request(
    request: Request,
    cancellation: RefreshCancellation | None = None,
    *,
    timeout: float = 30,
) -> Iterator[object]:
    if cancellation is not None:
        cancellation.raise_if_cancelled()
    with urlopen(request, timeout=resolve_request_timeout(cancellation, timeout)) as response:
        yield response


def read_text_response(
    response: object,
    cancellation: RefreshCancellation | None = None,
    *,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> str:
    return cancellable_read(response, cancellation).decode(encoding, errors=errors)


def read_text_url(
    url: str,
    cancellation: RefreshCancellation | None = None,
    *,
    headers: Mapping[str, str] | None = None,
    data: bytes | None = None,
    method: str | None = None,
    timeout: float = 30,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> str:
    request = build_request(
        url,
        headers=newsr_headers() if headers is None else headers,
        data=data,
        method=method,
    )
    with open_request(request, cancellation, timeout=timeout) as response:
        return read_text_response(response, cancellation, encoding=encoding, errors=errors)
