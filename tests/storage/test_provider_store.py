from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from newsr.domain import ProviderRecord, ProviderTarget


def test_storage_persists_provider_registry_and_targets(storage) -> None:
    storage.sync_providers(
        [ProviderRecord(provider_id="rss", display_name="RSS", enabled=False)]
    )
    storage.replace_provider_targets(
        "rss",
        [
            ProviderTarget(
                provider_id="rss",
                target_key="hn",
                target_kind="feed",
                label="Hacker News",
                payload={"url": "https://example.com/feed.xml"},
            )
        ],
    )
    storage.set_selected_targets("rss", ["hn"])

    providers = storage.list_providers()
    targets = storage.list_provider_targets("rss")

    assert any(provider.provider_id == "rss" and provider.enabled is False for provider in providers)
    assert targets == [
        ProviderTarget(
            provider_id="rss",
            target_key="hn",
            target_kind="feed",
            label="Hacker News",
            payload={"url": "https://example.com/feed.xml"},
            discovered_at=None,
            selected=True,
        )
    ]


def test_storage_creates_topic_provider_with_default_target(storage) -> None:
    provider = storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule="*/15 * * * *",
    )

    stored_provider = storage.get_provider(provider.provider_id)
    targets = storage.list_provider_targets(provider.provider_id)

    assert stored_provider is not None
    assert stored_provider.provider_type == "topic"
    assert stored_provider.update_schedule == "*/15 * * * *"
    assert stored_provider.settings == {"topic_query": "OpenAI policy"}
    assert targets == [
        ProviderTarget(
            provider_id=provider.provider_id,
            target_key="watch",
            target_kind="topic",
            label="OpenAI policy",
            payload={"query": "OpenAI policy"},
            discovered_at=None,
            selected=True,
        )
    ]


def test_storage_lists_due_providers_using_provider_override_and_default_schedule(storage) -> None:
    topic_provider = storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule="*/15 * * * *",
    )
    storage.mark_refresh_completed("bbc")
    storage.mark_refresh_completed(topic_provider.provider_id)
    stale_timestamp = datetime.now(UTC) - timedelta(hours=2)
    storage.connection.execute(
        """
        UPDATE providers
        SET last_refresh_completed_at = ?
        WHERE provider_id = ?
        """,
        (stale_timestamp.isoformat(), "bbc"),
    )
    storage.connection.execute(
        """
        UPDATE providers
        SET last_refresh_completed_at = ?
        WHERE provider_id = ?
        """,
        ((datetime.now(UTC) - timedelta(minutes=20)).isoformat(), topic_provider.provider_id),
    )
    storage.connection.commit()

    due_providers = storage.list_due_providers("0 * * * *")

    assert {provider.provider_id for provider in due_providers} == {"bbc", topic_provider.provider_id}


def test_storage_rejects_duplicate_topic_provider_names_case_insensitively(storage) -> None:
    storage.create_topic_provider(
        display_name="OpenAI policy",
        topic_query="OpenAI policy",
        update_schedule=None,
    )

    with pytest.raises(ValueError, match="OpenAI policy"):
        storage.create_topic_provider(
            display_name="  openai   policy  ",
            topic_query="  openai   policy  ",
            update_schedule=None,
        )
