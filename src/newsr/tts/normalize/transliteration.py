"""Cached English-to-Cyrillic transliteration: RUNorm first, then, ahead of synthesis, the LLM for words RUNorm can only spell."""

from __future__ import annotations

import json
import logging
import re
import warnings
from collections.abc import Callable, Mapping
from pathlib import Path
from threading import Lock

from ...cancellation import RefreshCancellation, RefreshCancelled

LOGGER = logging.getLogger("newsr.tts")
RUNORM_MODEL = "RUNorm/RUNorm-kirillizator"
CACHE_FILE_NAME = "transliterations.json"
LLM_BATCH_TERMS = 40

# Letter names RUNorm produces when it spells a word instead of transliterating it.
_SPELLED_LETTERS = frozenset({
    "эй", "би", "си", "ди", "эф", "джи", "эйч", "ай", "джей", "кей", "эль", "эл", "эм", "эн", "оу", "пи", "кью",
    "ар", "эр", "эс", "ти", "ю", "йю", "ви", "дабл", "дабл-ю", "экс", "икс", "уай", "зэд", "зед", "и",
})

Kirillize = Callable[[str], str]
LLMTransliterate = Callable[[list[str], RefreshCancellation | None], Mapping[str, str]]


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
    """Transliterates English terms for Russian speech.

    Calling the transliterator uses the cache and RUNorm only, so speech synthesis never waits for the LLM.
    `prepare` also asks the LLM for terms RUNorm can only spell; the playlist runs it when articles are queued.
    """

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
        # Terms RUNorm could only spell; `prepare` still sends them to the LLM.
        self._spelled: set[str] = set()
        # Terms the LLM could not transliterate either; they are spelled for the rest of the session.
        self._unresolved: set[str] = set()
        # Guards the cache, the term sets, and the cache file; held only briefly.
        self._lock = Lock()
        # Guards RUNorm loading and inference; never held together with `_lock`.
        self._model_lock = Lock()

    def __call__(self, terms: list[str]) -> dict[str, str]:
        self._runorm_pass(self._untried(terms))
        return self._cached(terms)

    def prepare(self, terms: list[str], cancellation: RefreshCancellation | None = None) -> dict[str, str]:
        self._runorm_pass(self._untried(terms), cancellation)
        llm = self._llm
        if llm is not None:
            with self._lock:
                spelled = [term for term in dict.fromkeys(terms) if term in self._spelled]
            for start in range(0, len(spelled), LLM_BATCH_TERMS):
                self._ask_llm(llm, spelled[start:start + LLM_BATCH_TERMS], cancellation)
        return self._cached(terms)

    def _untried(self, terms: list[str]) -> list[str]:
        with self._lock:
            cache = self._load_cache()
            return [
                term
                for term in dict.fromkeys(terms)
                if term not in cache and term not in self._spelled and term not in self._unresolved
            ]

    def _cached(self, terms: list[str]) -> dict[str, str]:
        with self._lock:
            cache = self._load_cache()
            return {term: cache[term] for term in terms if term in cache}

    def _runorm_pass(self, terms: list[str], cancellation: RefreshCancellation | None = None) -> None:
        found: dict[str, str] = {}
        spelled: list[str] = []
        for term in terms:
            if cancellation is not None:
                cancellation.raise_if_cancelled()
            output = self._runorm_transliteration(term)
            if output is None:
                spelled.append(term)
            else:
                found[term] = output
        if not found and not spelled:
            return
        with self._lock:
            self._spelled.update(spelled)
            if found:
                cache = self._load_cache()
                cache.update(found)
                self._save_cache(cache)

    def _runorm_transliteration(self, term: str) -> str | None:
        output = self._kirillize(term)
        if output is None:
            return None
        if not looks_spelled(output):
            return output
        words = term.split()
        if len(words) > 1:
            outputs = [self._kirillize(word) or "" for word in words]
            if not any(looks_spelled(word_output) for word_output in outputs):
                return " ".join(outputs)
        return None

    def _kirillize(self, text: str) -> str | None:
        with self._model_lock:
            if self._runorm is None and not self._runorm_failed:
                try:
                    self._runorm = self._runorm_loader(self._models_dir / "runorm")
                except Exception as exc:
                    self._runorm_failed = True
                    LOGGER.warning("transliteration_model_failed error_type=%s error=%s", type(exc).__name__, exc)
            if self._runorm is None:
                return None
            return self._runorm(text)

    def _ask_llm(self, llm: LLMTransliterate, terms: list[str], cancellation: RefreshCancellation | None) -> None:
        try:
            answer = llm(terms, cancellation)
        except RefreshCancelled:
            raise
        except Exception as exc:
            # Nothing is marked, so the next preparation asks again.
            LOGGER.warning("transliteration_llm_failed terms=%s error_type=%s error=%s", len(terms), type(exc).__name__, exc)
            return
        found = {
            term: str(answer[term]).strip().lower()
            for term in terms
            if answer.get(term) and not looks_spelled(str(answer[term]))
        }
        with self._lock:
            self._spelled.difference_update(terms)
            self._unresolved.update(term for term in terms if term not in found)
            if found:
                cache = self._load_cache()
                cache.update(found)
                self._save_cache(cache)

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
