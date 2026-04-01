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
    assert config.translation.target_language == "Serbian"
    assert config.ui.locale == "en"
    assert config.ui.show_all is True
    assert config.ui.provider_sort.primary == "unread"
    assert config.ui.provider_sort.direction == "desc"
    assert config.export.image.quality == "fhd"


def test_load_config_accepts_hosted_llm_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 7
  store: 14
llm:
  url: https://api.openai.com/v1
  model_translation: gpt-4.1-mini
  model_summary: gpt-4.1-mini
  api_key: sk-test
  headers:
    OpenAI-Organization: org-test
  request_retries: 3
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

    assert config.llm.url == "https://api.openai.com/v1"
    assert config.llm.api_key == "sk-test"
    assert config.llm.headers == {"OpenAI-Organization": "org-test"}
    assert config.llm.request_retries == 3
    assert config.ui.locale == "en"
    assert config.ui.show_all is True
    assert config.ui.provider_sort.primary == "unread"


def test_load_config_accepts_russian_ui_locale(tmp_path: Path) -> None:
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
  target_language: Russian
ui:
  locale: ru
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.ui.locale == "ru"
    assert config.ui.show_all is True
    assert config.ui.provider_sort.direction == "desc"


def test_load_config_accepts_provider_sort_overrides(tmp_path: Path) -> None:
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
  provider_sort:
    primary: name
    direction: asc
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.ui.provider_sort.primary == "name"
    assert config.ui.provider_sort.direction == "asc"


def test_load_config_accepts_show_all_override(tmp_path: Path) -> None:
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
  show-all: false
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.ui.show_all is False


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


def test_load_config_rejects_invalid_llm_headers(tmp_path: Path) -> None:
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
  headers:
    Invalid:
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

    with pytest.raises(ValueError, match="llm.headers"):
        load_config(config_path)


def test_load_config_rejects_negative_llm_retries(tmp_path: Path) -> None:
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
  request_retries: -1
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

    with pytest.raises(ValueError, match="llm.request_retries"):
        load_config(config_path)


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


def test_load_config_requires_ui_locale(tmp_path: Path) -> None:
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
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ui.locale"):
        load_config(config_path)


def test_load_config_rejects_invalid_provider_sort_primary(tmp_path: Path) -> None:
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
  provider_sort:
    primary: newest
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ui.provider_sort.primary"):
        load_config(config_path)


def test_load_config_rejects_invalid_provider_sort_direction(tmp_path: Path) -> None:
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
  provider_sort:
    direction: sideways
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ui.provider_sort.direction"):
        load_config(config_path)


def test_load_config_rejects_invalid_show_all_value(tmp_path: Path) -> None:
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
  show-all: maybe
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ui.show-all"):
        load_config(config_path)
