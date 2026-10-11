from __future__ import annotations

from pathlib import Path

import pytest

from newsr.config import load_config


def test_load_config_accepts_article_update_schedule_override(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 7
  store: 14
  update_schedule: "*/15 * * * *"
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

    assert config.articles.update_schedule == "*/15 * * * *"


def test_load_config_accepts_article_timeout_override(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 7
  store: 14
  timeout: 45
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

    assert config.articles.timeout == 45


def test_load_config_rejects_invalid_article_fetch(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 0
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
    quality: fhd
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_config(config_path)


def test_load_config_rejects_invalid_article_timeout(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 5
  store: 10
  timeout: 0
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
    quality: fhd
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="articles.timeout"):
        load_config(config_path)


def test_load_config_rejects_invalid_article_update_schedule(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 5
  store: 10
  update_schedule: "bad cron"
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
    quality: fhd
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cron expression"):
        load_config(config_path)
