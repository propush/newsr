from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from newsr.config import (
    AppConfig,
    ArticlesConfig,
    ExportConfig,
    ExportImageConfig,
    LLMConfig,
    ProviderSortConfig,
    TranslationConfig,
    UIConfig,
)
from newsr.domain import ArticleContent, ProviderRecord, ProviderTarget
from newsr.storage import NewsStorage


@pytest.fixture(autouse=True, scope="session")
def _isolate_llm_logger(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Prevent tests from writing to the real cache/newsr-llm.log file."""
    logger = logging.getLogger("newsr.llm")
    log_path = tmp_path_factory.mktemp("logs") / "newsr-llm.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    logger.addHandler(handler)
    yield
    logger.removeHandler(handler)
    handler.close()


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig(
        articles=ArticlesConfig(fetch=2, store=10, timeout=180, update_schedule="0 * * * *"),
        llm=LLMConfig(
            url="http://localhost:8081/v1",
            model_translation="translate",
            model_summary="summary",
            headers={},
        ),
        translation=TranslationConfig(target_language="Russian"),
        ui=UIConfig(
            locale="en",
            show_all=True,
            provider_sort=ProviderSortConfig(primary="unread", direction="desc"),
        ),
        export=ExportConfig(image=ExportImageConfig(quality="hd")),
    )


@pytest.fixture
def storage(tmp_path: Path) -> NewsStorage:
    db = NewsStorage(tmp_path / "newsr.sqlite3")
    db.initialize()
    db.sync_providers(
        [ProviderRecord(provider_id="bbc", display_name="BBC News", enabled=True, provider_type="http")]
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
