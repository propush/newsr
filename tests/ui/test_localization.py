from __future__ import annotations

import asyncio

from textual.widgets import Static

from newsr.ui import NewsReaderApp

from tests.ui.support.app_state import disable_startup_refresh
from tests.ui.support.reader import body_source, header_text, plain_content, url_source


def test_ui_keeps_mode_hotkey_fixed_when_localizing_labels(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    mode_bindings = app._bindings.get_bindings_for_key("s")

    assert len(mode_bindings) == 1
    assert mode_bindings[0].action == "cycle_view_mode"
    assert mode_bindings[0].description == "Mode"


def test_ui_keeps_classify_hotkey_fixed_when_localizing_labels(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    classify_bindings = app._bindings.get_bindings_for_key("k")

    assert len(classify_bindings) == 1
    assert classify_bindings[0].action == "classify_article_categories"
    assert classify_bindings[0].description == "Classify"


def test_ui_keeps_mode_hotkey_fixed_in_russian_locale(app_config, tmp_path) -> None:
    app_config.ui.locale = "ru"
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    mode_bindings = app._bindings.get_bindings_for_key("s")

    assert len(mode_bindings) == 1
    assert mode_bindings[0].action == "cycle_view_mode"
    assert mode_bindings[0].description == "Режим"


def test_ui_keeps_classify_hotkey_fixed_in_russian_locale(app_config, tmp_path) -> None:
    app_config.ui.locale = "ru"
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    classify_bindings = app._bindings.get_bindings_for_key("k")

    assert len(classify_bindings) == 1
    assert classify_bindings[0].action == "classify_article_categories"
    assert classify_bindings[0].description == "Категории"


def test_ui_renders_russian_copy_and_preserves_hotkeys(app_config, tmp_path, article_content) -> None:
    app_config.ui.locale = "ru"
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    disable_startup_refresh(app)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Переведённый заголовок", "Переведённый текст", "done")
    app.storage.update_summary(article_content.article_id, "Краткая сводка", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert "Статья № 1 из 1" in header_text(app)
            assert "Заголовок: Переведённый заголовок" in header_text(app)
            assert "Режим : полный" in header_text(app)
            assert url_source(app) == f"URL: {article_content.url}"

            await pilot.press("h")
            await pilot.pause()
            help_text = plain_content(app.screen.query_one("#help-text", Static).content)
            assert "K: классифицировать категории" in help_text
            assert "S: переключить режим чтения" in help_text
            assert "M: подробнее" in help_text
            assert "D: принудительно обновить текущего провайдера" in help_text
            await pilot.press("escape")
            await pilot.pause()

            await pilot.press("s")
            await pilot.pause()
            assert "Режим : сводка" in header_text(app)
            assert body_source(app) == "Краткая сводка"

    asyncio.run(runner())
