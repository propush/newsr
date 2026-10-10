from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from newsr.domain import ProviderRecord, ProviderTarget
from newsr.storage import NewsStorage
from newsr.ui import NewsReaderApp


def test_startup_updates_catalogs_without_resetting_user_state(app_config, tmp_path) -> None:
    path = tmp_path / "newsr.sqlite3"
    storage = NewsStorage(path)
    storage.initialize()
    storage.sync_providers([
        ProviderRecord("ninetofivegoogle", "9to5Google", True, update_schedule="0 8 * * *"),
        ProviderRecord("bbc", "BBC News", False),
        ProviderRecord("edsurge", "EdSurge", False),
    ])
    storage.replace_provider_targets("ninetofivegoogle", [
        ProviderTarget("ninetofivegoogle", "workspace", "category", "Workspace", {"path": "/guides/workspace/"}),
        ProviderTarget("ninetofivegoogle", "retired", "category", "Retired", {"path": "/retired/"}),
    ])
    storage.set_selected_targets("ninetofivegoogle", ["workspace", "retired"])
    discovered_at = datetime(2026, 10, 1, tzinfo=UTC)
    storage.replace_provider_targets("bbc", [
        ProviderTarget("bbc", "custom-section", "category", "Discovered", {"slug": "custom-section"}, discovered_at),
        ProviderTarget("bbc", "science-environment", "category", "Science", {"slug": "science-environment"}),
    ])
    storage.set_selected_targets("bbc", ["custom-section", "science-environment"])
    storage.replace_provider_targets("edsurge", [
        ProviderTarget("edsurge", "k12", "category", "K-12", {"path": "/news/k-12"}),
        ProviderTarget("edsurge", "higher-ed", "category", "Higher Ed", {"path": "/news/higher-ed"}),
    ])
    storage.set_selected_targets("edsurge", [])
    topic = storage.create_topic_provider(display_name="A watched topic", topic_query="example", update_schedule=None)
    watched_targets = storage.list_provider_targets(topic.provider_id)
    storage.close()

    app = NewsReaderApp(app_config, path)
    app._refresh.start = lambda *args, **kwargs: None

    async def runner() -> None:
        async with app.run_test():
            for _ in range(2):
                app._provider_home.bootstrap()
                google = {target.target_key: target for target in app.storage.list_provider_targets("ninetofivegoogle")}
                assert google["workspace"].payload["path"] == "/guides/google-workspace/"
                assert google["workspace"].selected is True
                assert google["gemini"].selected is False
                assert "retired" not in google
                bbc = {target.target_key: target for target in app.storage.list_provider_targets("bbc")}
                assert bbc["custom-section"].discovered_at == discovered_at
                assert bbc["custom-section"].selected is True
                assert bbc["science-environment"].selected is True
                assert bbc["science-environment"].payload["path"] == "/news/science_and_environment"
                assert bbc["arts"].selected is False
                edsurge = {target.target_key: target for target in app.storage.list_provider_targets("edsurge")}
                assert "k12" not in edsurge
                assert edsurge["higher-ed"].payload["path"] == "/coverage-areas/higher-education"
                assert app.storage.list_selected_targets("edsurge") == []
                assert app.storage.list_provider_targets(topic.provider_id) == watched_targets
                assert app.storage.get_provider("ninetofivegoogle").enabled is True
                assert app.storage.get_provider("ninetofivegoogle").update_schedule == "0 8 * * *"
                assert app.storage.get_provider("bbc").enabled is False

    asyncio.run(runner())


def test_manual_refresh_preserves_empty_selection(app_config, tmp_path) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    app._refresh.start = lambda *args, **kwargs: None
    app.storage.set_selected_targets("bbc", [])

    async def runner() -> None:
        async with app.run_test():
            targets = app._provider_home.refresh_catalog("bbc")
            assert targets
            assert not any(target.selected for target in targets)

    asyncio.run(runner())


def test_manual_refresh_does_not_select_defaults_when_selected_category_disappears(app_config, tmp_path, monkeypatch) -> None:
    app = NewsReaderApp(app_config, tmp_path / "newsr.sqlite3")
    app._refresh.start = lambda *args, **kwargs: None
    monkeypatch.setattr(app.providers["bbc"], "discover_targets", lambda: [
        ProviderTarget("bbc", "arts", "category", "Arts", {"path": "/arts"}, selected=True),
    ])

    async def runner() -> None:
        async with app.run_test():
            targets = app._provider_home.refresh_catalog("bbc")
            assert [target.target_key for target in targets] == ["arts"]
            assert app.storage.list_selected_targets("bbc") == []

    asyncio.run(runner())
