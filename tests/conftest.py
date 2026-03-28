from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from newsr.config import (
    AppConfig,
    ArticlesConfig,
    ExportConfig,
    ExportImageConfig,
    LLMConfig,
    TranslationConfig,
    UILocaleConfig,
)
from newsr.domain import ArticleContent, ProviderRecord, ProviderTarget
from newsr.storage import NewsStorage


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig(
        articles=ArticlesConfig(fetch=2, store=10),
        llm=LLMConfig(
            url="http://localhost:8081/v1",
            model_translation="translate",
            model_summary="summary",
            headers={},
        ),
        translation=TranslationConfig(target_language="Russian"),
        ui=UILocaleConfig(locale="en"),
        export=ExportConfig(image=ExportImageConfig(quality="hd")),
    )


@pytest.fixture
def storage(tmp_path: Path) -> NewsStorage:
    db = NewsStorage(tmp_path / "newsr.sqlite3")
    db.initialize()
    db.sync_providers(
        [ProviderRecord(provider_id="bbc", display_name="BBC News", enabled=True)]
    )
    db.replace_provider_targets(
        "bbc",
        [
            ProviderTarget(
                provider_id="bbc",
                target_key="world",
                target_kind="category",
                label="World",
                payload={"slug": "world"},
                selected=True,
            ),
            ProviderTarget(
                provider_id="bbc",
                target_key="technology",
                target_kind="category",
                label="Technology",
                payload={"slug": "technology"},
                selected=True,
            ),
        ],
    )
    db.set_selected_targets("bbc", ["world", "technology"])
    yield db
    db.close()


@pytest.fixture
def article_content() -> ArticleContent:
    return ArticleContent(
        article_id="bbc:test-1",
        provider_id="bbc",
        provider_article_id="test-1",
        url="https://www.bbc.com/news/test-1",
        category="world",
        title="Example title",
        author="Reporter",
        published_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
        body="Paragraph one.\n\nParagraph two.",
    )
