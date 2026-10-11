from __future__ import annotations

from dataclasses import dataclass

MIN_OUTPUT_TOKENS = 16
MAX_BATCH_OUTPUT_TOKENS = 1024
MAX_FINAL_OUTPUT_TOKENS = 2048


def estimate_token_count(value: str) -> int:
    return max(1, (len(value.encode("utf-8")) + 2) // 3)


def trim_to_budget(value: str, token_budget: int) -> str:
    if estimate_token_count(value) <= token_budget:
        return value
    char_budget = max(1, token_budget * 3)
    return value[:char_budget].rsplit(" ", 1)[0].strip() or value[:char_budget].strip()


@dataclass(frozen=True, slots=True)
class BriefBudget:
    context_tokens: int

    def batch_output_tokens(self) -> int:
        return max(MIN_OUTPUT_TOKENS, min(MAX_BATCH_OUTPUT_TOKENS, self.context_tokens // 4))

    def final_output_tokens(self) -> int:
        return max(MIN_OUTPUT_TOKENS, min(MAX_FINAL_OUTPUT_TOKENS, self.context_tokens // 3))

    def input_budget(self, prompt: str, output_tokens: int) -> int:
        prompt_tokens = estimate_token_count(prompt)
        budget = self.context_tokens - prompt_tokens - output_tokens
        if budget <= 0:
            raise ValueError("llm.brief_context is too small for brief generation")
        return budget

    def fits(self, prompt: str, content: str, output_tokens: int) -> bool:
        return estimate_token_count(prompt) + estimate_token_count(content) + output_tokens <= self.context_tokens
