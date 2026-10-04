from __future__ import annotations

import subprocess

import pytest

from newsr.export import ClipboardError, ClipboardManager


@pytest.mark.parametrize(
    ("system_name", "command", "encoding"),
    [("Darwin", ["pbcopy"], "utf-8"), ("Windows", ["clip"], "utf-16le")],
)
def test_native_text_command_preserves_unicode(monkeypatch, system_name, command, encoding) -> None:
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stderr=b"")

    monkeypatch.setattr(subprocess, "run", run)
    ClipboardManager(system_name, timeout=2).copy_text("Привет 🌍\nsecond line")

    assert calls == [(command, {
        "input": "Привет 🌍\nsecond line".encode(encoding),
        "capture_output": True, "check": False, "timeout": 2,
    })]


@pytest.mark.parametrize(
    ("wayland", "x11", "expected"),
    [(True, False, "wl-copy"), (False, True, "xclip"), (True, True, "wl-copy")],
)
def test_linux_selects_backend_for_display(monkeypatch, wayland, x11, expected) -> None:
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    if wayland:
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    if x11:
        monkeypatch.setenv("DISPLAY", ":0")
    manager = ClipboardManager("Linux", timeout=2)
    monkeypatch.setattr(manager, "_command_exists", lambda name: True)
    calls = []
    monkeypatch.setattr(manager, "_run", lambda command, **kwargs: calls.append((command, kwargs)))

    manager.copy_text("Привет\nworld")

    command, kwargs = calls[0]
    assert len(calls) == 1
    assert command == (
        ["wl-copy", "--type", "text/plain;charset=utf-8"] if expected == "wl-copy"
        else ["xclip", "-selection", "clipboard", "-in"]
    )
    assert kwargs["input_bytes"] == "Привет\nworld".encode("utf-8")
    assert kwargs["timeout"] == 2


def test_linux_tries_x11_after_wayland_failure(monkeypatch) -> None:
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("DISPLAY", ":0")
    manager = ClipboardManager("Linux")
    monkeypatch.setattr(manager, "_command_exists", lambda name: True)
    calls = []

    def run(command, **kwargs):
        calls.append(command[0])
        if command[0] == "wl-copy":
            raise ClipboardError("Wayland disconnected")

    monkeypatch.setattr(manager, "_run", run)
    manager.copy_text("text")
    assert calls == ["wl-copy", "xclip"]


@pytest.mark.parametrize("display_available", [False, True])
def test_linux_reports_missing_display_or_tools(monkeypatch, display_available) -> None:
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    if display_available:
        monkeypatch.setenv("DISPLAY", ":0")
    manager = ClipboardManager("Linux")
    monkeypatch.setattr(manager, "_command_exists", lambda name: not display_available)
    with pytest.raises(ClipboardError, match="requires"):
        manager.copy_text("text")


@pytest.mark.parametrize("failure", ["missing", "timeout", "exit"])
def test_command_failures_are_clipboard_errors(monkeypatch, failure) -> None:
    def run(command, **kwargs):
        if failure == "missing":
            raise FileNotFoundError("missing executable")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 2)
        return subprocess.CompletedProcess(command, 1, stderr=b"clipboard unavailable")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ClipboardError):
        ClipboardManager("Darwin", timeout=2).copy_text("text")
