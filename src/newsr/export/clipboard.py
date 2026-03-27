from __future__ import annotations

import base64
import os
import platform
import subprocess
import tempfile
from pathlib import Path


class ClipboardError(RuntimeError):
    pass


class ClipboardManager:
    def __init__(self, system_name: str | None = None) -> None:
        self.system_name = system_name or platform.system()

    def copy_text(self, text: str) -> None:
        if self.system_name == "Darwin":
            self._run(["pbcopy"], input_bytes=text.encode("utf-8"), error_prefix="pbcopy")
            return
        if self.system_name == "Linux":
            self._copy_text_linux(text)
            return
        if self.system_name == "Windows":
            self._run(["clip"], input_bytes=text.encode("utf-16le"), error_prefix="clip")
            return
        raise ClipboardError(f"clipboard text export is not supported on {self.system_name}")

    def copy_image(self, png_bytes: bytes) -> None:
        if self.system_name == "Darwin":
            self._copy_image_macos(png_bytes)
            return
        if self.system_name == "Linux":
            self._copy_image_linux(png_bytes)
            return
        if self.system_name == "Windows":
            self._copy_image_windows(png_bytes)
            return
        raise ClipboardError(f"clipboard image export is not supported on {self.system_name}")

    def _copy_text_linux(self, text: str) -> None:
        payload = text.encode("utf-8")
        if self._command_exists("wl-copy"):
            self._run(["wl-copy", "--type", "text/plain;charset=utf-8"], input_bytes=payload, error_prefix="wl-copy")
            return
        if self._command_exists("xclip"):
            self._run(
                ["xclip", "-selection", "clipboard", "-in"],
                input_bytes=payload,
                error_prefix="xclip",
            )
            return
        raise ClipboardError("clipboard text export requires wl-copy or xclip")

    def _copy_image_linux(self, png_bytes: bytes) -> None:
        if self._command_exists("wl-copy"):
            self._run(["wl-copy", "--type", "image/png"], input_bytes=png_bytes, error_prefix="wl-copy")
            return
        if self._command_exists("xclip"):
            self._run(
                ["xclip", "-selection", "clipboard", "-t", "image/png", "-in"],
                input_bytes=png_bytes,
                error_prefix="xclip",
            )
            return
        raise ClipboardError("clipboard image export requires wl-copy or xclip")

    def _copy_image_macos(self, png_bytes: bytes) -> None:
        with tempfile.NamedTemporaryFile(prefix="newsr-export-", suffix=".png", delete=False) as handle:
            handle.write(png_bytes)
            temp_path = Path(handle.name)
        try:
            escaped = str(temp_path).replace("\\", "\\\\").replace('"', '\\"')
            script = f'set the clipboard to (read (POSIX file "{escaped}") as «class PNGf»)'
            self._run(["osascript", "-e", script], error_prefix="osascript")
        finally:
            temp_path.unlink(missing_ok=True)

    def _copy_image_windows(self, png_bytes: bytes) -> None:
        payload = base64.b64encode(png_bytes).decode("ascii")
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            f"$bytes=[Convert]::FromBase64String('{payload}'); "
            "$stream=New-Object IO.MemoryStream(,$bytes); "
            "$image=[Drawing.Image]::FromStream($stream); "
            "[Windows.Forms.Clipboard]::SetImage($image)"
        )
        self._run(["powershell", "-sta", "-NoProfile", "-Command", script], error_prefix="powershell")

    @staticmethod
    def _command_exists(name: str) -> bool:
        for path in os.environ.get("PATH", "").split(os.pathsep):
            if not path:
                continue
            candidate = Path(path) / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return True
        return False

    @staticmethod
    def _run(command: list[str], *, input_bytes: bytes | None = None, error_prefix: str) -> None:
        try:
            completed = subprocess.run(command, input=input_bytes, capture_output=True, check=False)
        except FileNotFoundError as exc:
            raise ClipboardError(f"{error_prefix} is not available") from exc
        if completed.returncode == 0:
            return
        error_text = completed.stderr.decode("utf-8", errors="replace").strip() or f"exit code {completed.returncode}"
        raise ClipboardError(f"{error_prefix} failed: {error_text}")
