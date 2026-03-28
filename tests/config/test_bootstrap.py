from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

import newsr.config.bootstrap as bootstrap_module
from newsr.config import bootstrap_config, guess_translation_language, load_config


class PromptStub:
    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return next(self._responses)


class FakeTerminal(StringIO):
    def __init__(self, *, interactive: bool) -> None:
        super().__init__()
        self._interactive = interactive

    def isatty(self) -> bool:
        return self._interactive


def test_bootstrap_config_creates_local_config_with_locale_suggestion(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    prompt = PromptStub(["", "", "", "", "", ""])
    secret_prompt = PromptStub([])
    output = StringIO()

    created = bootstrap_config(
        config_path,
        input_func=prompt,
        secret_input_func=secret_prompt,
        output=output,
        locale_name="sr_RS.UTF-8",
    )

    config = load_config(config_path)

    assert created is True
    assert config.ui.locale == "en"
    assert config.llm.url == "http://localhost:8081/v1"
    assert config.llm.model_translation == "local-translate"
    assert config.llm.model_summary == "local-translate"
    assert config.translation.target_language == "Serbian"
    assert config.export.image.quality == "fhd"
    assert "Suggested UI language from locale: English" in output.getvalue()
    assert "Suggested translation language from locale: Serbian" in output.getvalue()
    assert "Additional settings can be tuned by editing newsr.yml." in output.getvalue()
    assert prompt.prompts[0] == "UI language [English]: "
    assert prompt.prompts[-1] == "Press Enter to continue..."


def test_bootstrap_config_creates_cloud_config_and_retries_bad_headers(tmp_path: Path) -> None:
    config_path = tmp_path / "newsr.yml"
    prompt = PromptStub(
        [
            "",
            "cloud",
            "",
            "",
            "broken",
            "OpenAI-Organization=org-test, X-Custom=value",
            "German",
            "",
        ]
    )
    secret_prompt = PromptStub(["sk-test"])
    output = StringIO()

    bootstrap_config(
        config_path,
        input_func=prompt,
        secret_input_func=secret_prompt,
        output=output,
        locale_name="fr_FR.UTF-8",
    )

    config = load_config(config_path)

    assert config.llm.url == "https://api.openai.com/v1"
    assert config.llm.model_translation == "gpt-4.1-mini"
    assert config.llm.model_summary == "gpt-4.1-mini"
    assert config.llm.api_key == "sk-test"
    assert config.ui.locale == "en"
    assert config.llm.headers == {
        "OpenAI-Organization": "org-test",
        "X-Custom": "value",
    }
    assert config.translation.target_language == "German"
    assert "Headers must use the format Header=Value." in output.getvalue()


def test_guess_translation_language_falls_back_to_english_for_unknown_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap_module, "_detect_locale_name", lambda: None)
    assert guess_translation_language("xx_YY.UTF-8") == "English"
    assert guess_translation_language(None) == "English"


def test_ensure_config_requires_interactive_terminal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "newsr.yml"
    monkeypatch.setattr(bootstrap_module.sys, "stdin", FakeTerminal(interactive=False))
    monkeypatch.setattr(bootstrap_module.sys, "stdout", FakeTerminal(interactive=False))

    with pytest.raises(RuntimeError, match="first-run setup requires an interactive terminal"):
        bootstrap_module.ensure_config(config_path)


def test_ensure_ui_locale_updates_existing_config_before_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "newsr.yml"
    config_path.write_text(
        """
articles:
  fetch: 5
  store: 10
llm:
  url: http://localhost:8081/v1
  model_translation: local-translate
  model_summary: local-translate
translation:
  target_language: English
export:
  image:
    quality: fhd
""",
        encoding="utf-8",
    )
    prompt = PromptStub([""])
    output = StringIO()
    monkeypatch.setattr(bootstrap_module.sys, "stdin", FakeTerminal(interactive=True))
    monkeypatch.setattr(bootstrap_module.sys, "stdout", FakeTerminal(interactive=True))

    selected_locale = bootstrap_module.ensure_ui_locale(
        config_path,
        input_func=prompt,
        output=output,
        locale_name="en_US.UTF-8",
    )

    config = load_config(config_path)

    assert selected_locale == "en"
    assert config.ui.locale == "en"
    assert prompt.prompts == ["UI language [English]: "]
    assert "Saved UI language: English" in output.getvalue()
