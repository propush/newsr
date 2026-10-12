"""Cached English-to-Cyrillic transliteration: RUNorm first, the LLM for words RUNorm can only spell."""

from __future__ import annotations

import json
import logging
import re
import warnings
from collections.abc import Callable, Mapping
from pathlib import Path
from threading import Lock

LOGGER = logging.getLogger("newsr.tts")
RUNORM_MODEL = "RUNorm/RUNorm-kirillizator"
CACHE_FILE_NAME = "transliterations.json"

# Letter names RUNorm produces when it spells a word instead of transliterating it.
_SPELLED_LETTERS = frozenset({
    "эй", "би", "си", "ди", "эф", "джи", "эйч", "ай", "джей", "кей", "эль", "эл", "эм", "эн", "оу", "пи", "кью",
    "ар", "эр", "эс", "ти", "ю", "йю", "ви", "дабл", "дабл-ю", "экс", "икс", "уай", "зэд", "зед", "и",
})

Kirillize = Callable[[str], str]
LLMTransliterate = Callable[[list[str]], Mapping[str, str]]


def looks_spelled(output: str) -> bool:
    """True when a transliteration is empty, still Latin, or two or more letter names in a row."""
    if not output.strip() or re.search(r"[A-Za-z]", output):
        return True
    run = 0
    for word in output.replace("-", " ").split():
        run = run + 1 if word in _SPELLED_LETTERS else 0
        if run >= 2:
            return True
    return False


def load_runorm(cache_dir: Path) -> Kirillize:
    from huggingface_hub.utils import disable_progress_bars
    from huggingface_hub.utils import logging as hub_logging
    from transformers import AutoTokenizer, T5ForConditionalGeneration
    from transformers.utils import logging as transformers_logging

    # Progress bars and warnings on stderr would corrupt the terminal UI.
    disable_progress_bars()
    hub_logging.set_verbosity_error()
    transformers_logging.disable_progress_bar()
    transformers_logging.set_verbosity_error()

    def load(local_only: bool):
        options = {"cache_dir": str(cache_dir), "local_files_only": local_only}
        tokenizer = AutoTokenizer.from_pretrained(RUNORM_MODEL, **options)
        return tokenizer, T5ForConditionalGeneration.from_pretrained(RUNORM_MODEL, **options).eval()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            tokenizer, model = load(local_only=True)
        except OSError:
            LOGGER.info("download_start engine=silero model=%s", RUNORM_MODEL)
            tokenizer, model = load(local_only=False)

    def kirillize(text: str) -> str:
        inputs = tokenizer("<pad><pad><pad>" + text, return_tensors="pt")
        inputs.pop("token_type_ids", None)
        output = model.generate(**inputs, do_sample=False, max_new_tokens=128)[0]
        return tokenizer.decode(output.tolist(), skip_special_tokens=True).strip().lower()

    return kirillize


class TermTransliterator:
    def __init__(
        self,
        models_dir: Path,
        *,
        llm: LLMTransliterate | None = None,
        runorm_loader: Callable[[Path], Kirillize] = load_runorm,
    ) -> None:
        self._models_dir = models_dir
        self._cache_path = models_dir / CACHE_FILE_NAME
        self._llm = llm
        self._runorm_loader = runorm_loader
        self._runorm: Kirillize | None = None
        self._runorm_failed = False
        self._cache: dict[str, str] | None = None
        # Terms neither model could transliterate; they are spelled for the rest of the session.
        self._unresolved: set[str] = set()
        self._lock = Lock()

    def __call__(self, terms: list[str]) -> dict[str, str]:
        with self._lock:
            cache = self._load_cache()
            missing = [term for term in terms if term not in cache and term not in self._unresolved]
            if missing:
                found = self._transliterate(missing)
                self._unresolved.update(term for term in missing if term not in found)
                if found:
                    cache.update(found)
                    self._save_cache(cache)
            return {term: cache[term] for term in terms if term in cache}

    def _transliterate(self, terms: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        spelled: list[str] = []
        kirillize = self._kirillize()
        for term in terms:
            output = kirillize(term) if kirillize else ""
            if not looks_spelled(output):
                result[term] = output
                continue
            words = term.split()
            if kirillize and len(words) > 1:
                outputs = [kirillize(word) for word in words]
                if not any(looks_spelled(word_output) for word_output in outputs):
                    result[term] = " ".join(outputs)
                    continue
            spelled.append(term)
        if spelled and self._llm is not None:
            result.update(self._ask_llm(spelled))
        return result

    def _kirillize(self) -> Kirillize | None:
        if self._runorm is None and not self._runorm_failed:
            try:
                self._runorm = self._runorm_loader(self._models_dir / "runorm")
            except Exception as exc:
                self._runorm_failed = True
                LOGGER.warning("transliteration_model_failed error_type=%s error=%s", type(exc).__name__, exc)
        return self._runorm

    def _ask_llm(self, terms: list[str]) -> dict[str, str]:
        try:
            answer = self._llm(terms)
        except Exception as exc:
            LOGGER.warning("transliteration_llm_failed terms=%s error_type=%s error=%s", len(terms), type(exc).__name__, exc)
            return {}
        return {
            term: str(answer[term]).strip().lower()
            for term in terms
            if answer.get(term) and not looks_spelled(str(answer[term]))
        }

    def _load_cache(self) -> dict[str, str]:
        if self._cache is None:
            try:
                raw = json.loads(self._cache_path.read_text(encoding="utf-8"))
                self._cache = {str(key): str(value) for key, value in raw.items()} if isinstance(raw, dict) else {}
            except (OSError, ValueError):
                self._cache = {}
        return self._cache

    def _save_cache(self, cache: dict[str, str]) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        partial = self._cache_path.with_name(f"{self._cache_path.name}.part")
        partial.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        partial.replace(self._cache_path)
