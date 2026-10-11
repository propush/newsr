from __future__ import annotations

from pathlib import Path

import pytest

from newsr.config import load_config


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


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("none", "none"),
        ("SECONDS", "seconds"),
        ('" no_seconds "', "no_seconds"),
    ],
)
def test_load_config_accepts_clock_modes(
    tmp_path: Path,
    configured: str,
    expected: str,
) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        f"""
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
  clock: {configured}
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.ui.clock == expected


@pytest.mark.parametrize("configured", ["null", "true", "15", "minutes"])
def test_load_config_rejects_invalid_clock_modes(tmp_path: Path, configured: str) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        f"""
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
  clock: {configured}
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ui.clock must be one of"):
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
