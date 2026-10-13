from __future__ import annotations

import sys

import pytest

from newsr.tts.media_controls import NullMediaControls, build_media_controls
from newsr.tts.media_controls.macos import MacMediaControls

from tests.tts.media_controls.fakes import install_fake_macos_modules


def test_build_media_controls_returns_null_controls_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_macos_modules(monkeypatch)
    monkeypatch.setattr(sys, "platform", "darwin")

    assert isinstance(build_media_controls(False), NullMediaControls)


def test_build_media_controls_selects_the_macos_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_macos_modules(monkeypatch)
    monkeypatch.setattr(sys, "platform", "darwin")

    assert isinstance(build_media_controls(True), MacMediaControls)


@pytest.mark.parametrize(
    ("platform", "missing_modules"),
    [
        ("darwin", ("MediaPlayer",)),
        ("linux", ("dbus_fast", "newsr.tts.media_controls.mpris")),
        ("win32", ("winrt", "winrt.windows", "winrt.windows.media", "newsr.tts.media_controls.windows")),
        ("sunos5", ()),
    ],
)
def test_build_media_controls_falls_back_to_null_controls_without_platform_packages(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    missing_modules: tuple[str, ...],
) -> None:
    for module in missing_modules:
        monkeypatch.setitem(sys.modules, module, None)
    monkeypatch.setattr(sys, "platform", platform)

    assert isinstance(build_media_controls(True), NullMediaControls)
