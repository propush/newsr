from __future__ import annotations

from pathlib import Path

from ..config import ensure_config, ensure_ui_locale, load_config
from ..ui.app import NewsReaderApp


def main() -> None:
    root = Path.cwd()
    config_path = root / "newsr.yml"
    ensure_ui_locale(config_path)
    ensure_config(config_path)
    config = load_config(config_path)
    app = NewsReaderApp(config=config, storage_path=root / "cache" / "newsr.sqlite3", config_path=config_path)
    app.run()


if __name__ == "__main__":
    main()
