from __future__ import annotations

from ..providers.llm.client import current_datetime_prompt_value
from .models import Clock
from .repair import format_numbers


class BriefPrompts:
    def __init__(self, target_language: str, current_time: Clock | None = None) -> None:
        self._target_language = target_language
        self._current_time = current_time

    def batch(self) -> str:
        return (
            "Shorten these news summaries into compact brief notes in "
            f"{self._target_language}. "
            f"Current local date and time: {self._current_datetime()}. "
            "Keep only distinct important facts. Preserve source markers like [1]. "
            "Return concise Markdown bullets."
        )

    def final(self) -> str:
        return (
            f"Markdown brief in {self._target_language}: "
            f"Current local date and time: {self._current_datetime()}. "
            "# title; ## topic sections separated by ---; bullets per topic. "
            "Group related items, remove repetition, preserve source markers like [1]."
        )

    def batch_repair(self, required_numbers: frozenset[int]) -> str:
        return (
            f"Repair brief notes in {self._target_language}. "
            f"Time: {self._current_datetime()}. "
            f"Use only these markers and cite each once: {format_numbers(required_numbers)}. "
            "Every fact line needs a marker. Remove unsupported or invalid facts. Return bullets only."
        )

    def final_repair(self, required_numbers: frozenset[int]) -> str:
        return (
            f"Repair Markdown brief in {self._target_language}. "
            f"Time: {self._current_datetime()}. "
            f"Use only these markers and cite each once: {format_numbers(required_numbers)}. "
            "Every fact line needs a marker. Remove unsupported or invalid facts. Return brief only."
        )

    def _current_datetime(self) -> str:
        if self._current_time is None:
            return current_datetime_prompt_value()
        return current_datetime_prompt_value(self._current_time())
