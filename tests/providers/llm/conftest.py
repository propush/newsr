from __future__ import annotations

import http.client

import pytest

from tests.providers.llm.http_fakes import FakeHTTPConnection, FakeHTTPSConnection


@pytest.fixture(autouse=True)
def reset_fake_connections(monkeypatch) -> None:
    FakeHTTPConnection.plan = []
    FakeHTTPConnection.requests = []
    FakeHTTPConnection.instances = []
    FakeHTTPSConnection.plan = []
    FakeHTTPSConnection.requests = []
    FakeHTTPSConnection.instances = []
    monkeypatch.setattr(http.client, "HTTPConnection", FakeHTTPConnection)
    monkeypatch.setattr(http.client, "HTTPSConnection", FakeHTTPSConnection)
