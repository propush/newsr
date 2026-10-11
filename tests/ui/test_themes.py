from __future__ import annotations

import asyncio

from newsr.domain import AppOptions, ViewMode
from newsr.ui import OLD_FIDO_THEME, NewsReaderApp
from newsr.ui.themes import BRIEF_ARTICLE_REFERENCE_COLOR


def test_ui_applies_saved_theme_on_startup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    seeded_app = NewsReaderApp(app_config, storage_path)
    seeded_app.storage.save_reader_state(
        "[ALL]",
        seeded_app.reader_state.__class__(
            article_id=None,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        )
    )
    seeded_app.storage.save_options(AppOptions(theme_name="gruvbox"))
    seeded_app.storage.upsert_article_source(article_content)
    seeded_app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    seeded_app.storage.close()
    app = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.theme == "gruvbox"

    asyncio.run(runner())


def test_ui_persists_theme_changes(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    app = NewsReaderApp(app_config, storage_path)
    app.storage.upsert_article_source(article_content)
    app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            app.theme = "gruvbox"
            await pilot.pause()
            options = app.storage.load_options()
            assert options.theme_name == "gruvbox"

    asyncio.run(runner())


def test_ui_registers_old_fido_theme(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    theme = app.get_theme("old fido")

    assert theme == OLD_FIDO_THEME
    assert theme.primary == "#d8c24a"
    assert theme.accent == "#c8c8c8"
    assert theme.background == "#000000"
    assert theme.variables[BRIEF_ARTICLE_REFERENCE_COLOR] == "#d8c24a"
    app.theme = "old fido"
    assert app.get_css_variables()[BRIEF_ARTICLE_REFERENCE_COLOR] == "#d8c24a"


def test_ui_defaults_brief_article_reference_color_to_active_theme_accent(
    app_config, tmp_path
) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")

    assert app.current_theme.accent is not None
    assert (
        app.get_theme_variable_defaults()[BRIEF_ARTICLE_REFERENCE_COLOR]
        == app.current_theme.accent
    )


def test_ui_ignores_invalid_saved_theme(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    seeded_app = NewsReaderApp(app_config, storage_path)
    default_theme = seeded_app.theme
    seeded_app.storage.save_reader_state(
        "[ALL]",
        seeded_app.reader_state.__class__(
            article_id=None,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        )
    )
    seeded_app.storage.save_options(AppOptions(theme_name="not-a-theme"))
    seeded_app.storage.upsert_article_source(article_content)
    seeded_app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    seeded_app.storage.close()
    app = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.theme == default_theme

    asyncio.run(runner())


def test_ui_applies_saved_old_fido_theme_on_startup(app_config, tmp_path, article_content) -> None:
    storage_path = tmp_path / "newsr.sqlite3"
    seeded_app = NewsReaderApp(app_config, storage_path)
    seeded_app.storage.save_reader_state(
        "[ALL]",
        seeded_app.reader_state.__class__(
            article_id=None,
            view_mode=ViewMode.FULL,
            scroll_offset=0,
        )
    )
    seeded_app.storage.save_options(AppOptions(theme_name="old fido"))
    seeded_app.storage.upsert_article_source(article_content)
    seeded_app.storage.update_translation(article_content.article_id, "Translated title", "Translated text", "done")
    seeded_app.storage.close()
    app = NewsReaderApp(app_config, storage_path)

    async def runner() -> None:
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.theme == "old fido"

    asyncio.run(runner())


def test_ui_css_uses_textual_theme_tokens() -> None:
    assert "$background" in NewsReaderApp.CSS
    assert "$primary" in NewsReaderApp.CSS
    assert "$success" in NewsReaderApp.CSS
    assert "ansi_bright" not in NewsReaderApp.CSS
    assert "background: black;" not in NewsReaderApp.CSS
