from __future__ import annotations

from pathlib import Path

import pytest

from newsr.config import load_config


def test_load_config_requires_existing_file(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"

    with pytest.raises(FileNotFoundError):
        load_config(config_path)


def test_load_config_preserves_non_provider_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 7
  store: 14
llm:
  url: http://localhost:8081/v1
  model_translation: translate
  model_summary: summary
translation:
  target_language: Serbian
ui:
  locale: en
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.articles.fetch == 7
    assert config.articles.store == 14
    assert config.articles.timeout == 180
    assert config.articles.update_schedule == "0 * * * *"
    assert config.translation.target_language == "Serbian"
    assert config.ui.locale == "en"
    assert config.ui.clock == "no_seconds"
    assert config.ui.show_all is True
    assert config.ui.provider_sort.primary == "unread"
    assert config.ui.provider_sort.direction == "desc"
    assert config.export.image.quality == "fhd"
    assert config.llm.brief_context == 100000


def test_load_config_rejects_invalid_export_quality(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 5
  store: 10
llm:
  url: http://localhost:8081/v1
  model_translation: translate
  model_summary: summary
translation:
  target_language: Russian
ui:
  locale: en
export:
  image:
    quality: ultra
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="export.image.quality"):
        load_config(config_path)
