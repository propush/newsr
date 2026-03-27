from __future__ import annotations

import getpass
import locale
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO

import yaml

DEFAULT_ARTICLES_FETCH = 5
DEFAULT_ARTICLES_STORE = 10
DEFAULT_REQUEST_RETRIES = 2
DEFAULT_EXPORT_IMAGE_QUALITY = "fhd"

DEFAULT_LOCAL_URL = "http://localhost:8081/v1"
DEFAULT_LOCAL_MODEL = "local-translate"
DEFAULT_CLOUD_URL = "https://api.openai.com/v1"
DEFAULT_CLOUD_MODEL = "gpt-4.1-mini"
DEFAULT_TRANSLATION_LANGUAGE = "English"

LANGUAGE_BY_LOCALE = {
    "bg": "Bulgarian",
    "cs": "Czech",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hr": "Croatian",
    "hu": "Hungarian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sr": "Serbian",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "zh": "Chinese",
}


PromptFunc = Callable[[str], str]


@dataclass(slots=True)
class BootstrapAnswers:
    llm_url: str
    llm_model: str
    translation_language: str
    api_key: str | None = None
    headers: dict[str, str] | None = None
    articles_fetch: int = DEFAULT_ARTICLES_FETCH
    articles_store: int = DEFAULT_ARTICLES_STORE
    request_retries: int = DEFAULT_REQUEST_RETRIES
    export_image_quality: str = DEFAULT_EXPORT_IMAGE_QUALITY


def ensure_config(path: Path) -> bool:
    if path.exists():
        return False
    if not _is_interactive_terminal(sys.stdin, sys.stdout):
        raise RuntimeError(
            f"{path.name} was not found and first-run setup requires an interactive terminal. "
            f"Create {path.name} manually and rerun NewsR."
        )
    return bootstrap_config(path, input_func=input, secret_input_func=getpass.getpass, output=sys.stdout)


def bootstrap_config(
    path: Path,
    *,
    input_func: PromptFunc,
    secret_input_func: PromptFunc,
    output: TextIO,
    locale_name: str | None = None,
) -> bool:
    answers = prompt_bootstrap_answers(
        input_func=input_func,
        secret_input_func=secret_input_func,
        output=output,
        locale_name=locale_name,
    )
    path.write_text(render_config(answers), encoding="utf-8")
    output.write(
        f"\nCreated {path.name}.\n"
        f"Additional settings can be tuned by editing {path.name}.\n"
    )
    input_func("Press Enter to continue...")
    return True


def prompt_bootstrap_answers(
    *,
    input_func: PromptFunc,
    secret_input_func: PromptFunc,
    output: TextIO,
    locale_name: str | None = None,
) -> BootstrapAnswers:
    output.write("No newsr.yml found. Let's create it.\n\n")
    backend = _prompt_backend(input_func, output)
    if backend == "cloud":
        llm_url = _prompt_with_default(input_func, "Cloud API URL", DEFAULT_CLOUD_URL)
        llm_model = _prompt_with_default(input_func, "Cloud model", DEFAULT_CLOUD_MODEL)
        api_key = _prompt_optional_secret(secret_input_func, "Cloud API key (optional)")
        headers = _prompt_optional_headers(input_func, output)
    else:
        llm_url = _prompt_with_default(input_func, "Local API URL", DEFAULT_LOCAL_URL)
        llm_model = _prompt_with_default(input_func, "Local model", DEFAULT_LOCAL_MODEL)
        api_key = None
        headers = {}

    translation_language = _prompt_translation_language(input_func, output, locale_name)
    return BootstrapAnswers(
        llm_url=llm_url,
        llm_model=llm_model,
        translation_language=translation_language,
        api_key=api_key,
        headers=headers,
    )


def render_config(answers: BootstrapAnswers) -> str:
    llm_config: dict[str, object] = {
        "url": answers.llm_url,
        "model_translation": answers.llm_model,
        "model_summary": answers.llm_model,
        "request_retries": answers.request_retries,
    }
    if answers.api_key:
        llm_config["api_key"] = answers.api_key
    if answers.headers:
        llm_config["headers"] = answers.headers

    raw_config = {
        "articles": {
            "fetch": answers.articles_fetch,
            "store": answers.articles_store,
        },
        "llm": llm_config,
        "translation": {
            "target_language": answers.translation_language,
        },
        "export": {
            "image": {
                "quality": answers.export_image_quality,
            }
        },
    }
    return yaml.safe_dump(raw_config, sort_keys=False, allow_unicode=True)


DEFAULT_CONFIG = render_config(
    BootstrapAnswers(
        llm_url=DEFAULT_LOCAL_URL,
        llm_model=DEFAULT_LOCAL_MODEL,
        translation_language=DEFAULT_TRANSLATION_LANGUAGE,
    )
)


def guess_translation_language(locale_name: str | None = None) -> str:
    resolved_locale = locale_name or _detect_locale_name()
    if not resolved_locale:
        return DEFAULT_TRANSLATION_LANGUAGE
    normalized_locale = resolved_locale.split(".", 1)[0].split("@", 1)[0]
    language_code = normalized_locale.replace("-", "_").split("_", 1)[0].lower()
    return LANGUAGE_BY_LOCALE.get(language_code, DEFAULT_TRANSLATION_LANGUAGE)


def _detect_locale_name() -> str | None:
    for key in ("LC_ALL", "LC_CTYPE", "LANG"):
        value = os.environ.get(key)
        if value:
            return value
    try:
        detected_locale, _ = locale.getlocale()
    except ValueError:
        return None
    return detected_locale


def _is_interactive_terminal(stdin: TextIO, stdout: TextIO) -> bool:
    return bool(getattr(stdin, "isatty", lambda: False)() and getattr(stdout, "isatty", lambda: False)())


def _prompt_backend(input_func: PromptFunc, output: TextIO) -> str:
    while True:
        response = input_func("LLM backend [local/cloud] (default: local): ").strip().lower()
        if not response:
            return "local"
        if response in {"local", "l"}:
            return "local"
        if response in {"cloud", "c"}:
            return "cloud"
        output.write("Please enter 'local' or 'cloud'.\n")


def _prompt_with_default(input_func: PromptFunc, prompt: str, default: str) -> str:
    response = input_func(f"{prompt} [{default}]: ").strip()
    return response or default


def _prompt_optional_secret(secret_input_func: PromptFunc, prompt: str) -> str | None:
    response = secret_input_func(f"{prompt}: ").strip()
    return response or None


def _prompt_translation_language(input_func: PromptFunc, output: TextIO, locale_name: str | None) -> str:
    suggested_language = guess_translation_language(locale_name)
    output.write(f"Suggested translation language from locale: {suggested_language}\n")
    return _prompt_with_default(input_func, "Translation language", suggested_language)


def _prompt_optional_headers(input_func: PromptFunc, output: TextIO) -> dict[str, str]:
    output.write(
        "Optional extra headers: enter comma-separated pairs like "
        "'OpenAI-Organization=org-123, X-Custom=value'. Leave blank for none.\n"
    )
    while True:
        response = input_func("Cloud headers: ").strip()
        if not response:
            return {}
        try:
            return _parse_headers(response)
        except ValueError as exc:
            output.write(f"{exc}\n")


def _parse_headers(raw_headers: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for part in raw_headers.split(","):
        pair = part.strip()
        if not pair:
            raise ValueError("Header list contains an empty entry. Use Header=Value pairs.")
        if "=" not in pair:
            raise ValueError("Headers must use the format Header=Value.")
        name, value = pair.split("=", 1)
        header_name = name.strip()
        header_value = value.strip()
        if not header_name or not header_value:
            raise ValueError("Headers must use non-empty Header=Value pairs.")
        headers[header_name] = header_value
    return headers
