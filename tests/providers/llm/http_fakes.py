from __future__ import annotations

import json

from newsr.config import (
    AppConfig,
    ArticlesConfig,
    ExportConfig,
    ExportImageConfig,
    LLMConfig,
    ProviderSortConfig,
    TranslationConfig,
    UIConfig,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object], *, status: int = 200) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self, _size: int = -1) -> bytes:
        if _size < 0:
            data = self._body
            self._body = b""
            return data
        if not self._body:
            return b""
        data = self._body[:_size]
        self._body = self._body[_size:]
        return data

    def close(self) -> None:
        return None


class FakeHTTPConnection:
    plan: list[object] = []
    requests: list[dict[str, object]] = []
    instances: list["FakeHTTPConnection"] = []

    def __init__(self, host: str, port: int, timeout: int = 300) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.closed = False
        self.sock = None
        self.__class__.instances.append(self)

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.__class__.requests.append(
            {
                "host": self.host,
                "port": self.port,
                "method": method,
                "path": path,
                "body": body,
                "headers": dict(headers or {}),
            }
        )
        if not self.__class__.plan:
            raise AssertionError("No fake response plan configured")
        current = self.__class__.plan[0]
        if isinstance(current, Exception):
            self.__class__.plan.pop(0)
            raise current

    def getresponse(self) -> FakeResponse:
        if not self.__class__.plan:
            raise AssertionError("No fake response plan configured")
        current = self.__class__.plan.pop(0)
        if isinstance(current, Exception):
            raise AssertionError("Exceptions should be raised during request()")
        return current

    def close(self) -> None:
        self.closed = True


class FakeHTTPSConnection(FakeHTTPConnection):
    pass


def make_config(
    *,
    url: str = "http://localhost:8081/v1",
    api_key: str | None = None,
    headers: dict[str, str] | None = None,
    request_retries: int = 2,
) -> AppConfig:
    return AppConfig(
        articles=ArticlesConfig(fetch=2, store=10, timeout=180, update_schedule="0 * * * *"),
        llm=LLMConfig(
            url=url,
            model_translation="translate",
            model_summary="summary",
            api_key=api_key,
            headers=headers or {},
            request_retries=request_retries,
        ),
        translation=TranslationConfig(target_language="Russian"),
        ui=UIConfig(
            locale="en",
            show_all=True,
            provider_sort=ProviderSortConfig(primary="unread", direction="desc"),
        ),
        export=ExportConfig(image=ExportImageConfig(quality="hd")),
    )
