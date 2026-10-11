from __future__ import annotations

from pathlib import Path

import pytest

from newsr.config import load_config


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
    assert config.llm.brief_context == 100000
    assert config.ui.locale == "en"
    assert config.ui.show_all is True
    assert config.ui.provider_sort.primary == "unread"


def test_load_config_accepts_brief_context_override(tmp_path: Path) -> None:
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
  brief_context: 2048
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

    assert config.llm.brief_context == 2048


def test_load_config_rejects_non_positive_brief_context(tmp_path: Path) -> None:
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
  brief_context: 0
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

    with pytest.raises(ValueError, match="llm.brief_context must be positive"):
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
