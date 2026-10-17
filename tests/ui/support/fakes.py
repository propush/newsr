from __future__ import annotations

from newsr.cancellation import RefreshCancellation
from newsr.domain import ViewMode
from newsr.export import ExportAction, ExportResult
from newsr.providers.search import SearchResult


class FakeSearchClient:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.calls: list[str] = []

    def search(
        self, query: str, limit: int = 5, cancellation: RefreshCancellation | None = None
    ) -> list[SearchResult]:
        self.calls.append(query)
        return self.results[:limit]


class FakeMoreInfoLLM:
    def __init__(self, *, query: str = "example query", responses: list[str] | None = None) -> None:
        self.query = query
        self.responses = responses or ["More info result"]
        self.query_calls: list[tuple[str, str]] = []
        self.synthesis_calls: list[tuple[str, str, list[SearchResult]]] = []

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        return None

    def build_search_query(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.query_calls.append((article_title, article_text))
        return self.query

    def synthesize_more_info(
        self,
        article_title: str,
        article_text: str,
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.synthesis_calls.append((article_title, article_text, search_results))
        index = min(len(self.synthesis_calls) - 1, len(self.responses) - 1)
        return self.responses[index]


class FakeArticleQALLM:
    def __init__(self, *, query: str = "latest context", answers: list[str] | None = None) -> None:
        self.query = query
        self.answers = answers or ["Article answer"]
        self.query_calls: list[tuple[str, str, str, str, list[tuple[str, str]]]] = []
        self.answer_calls: list[tuple[str, str, str, str, list[tuple[str, str]], list[SearchResult]]] = []

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        return None

    def build_article_question_query(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.query_calls.append((article_title, article_text, question, current_datetime, list(chat_history)))
        return self.query

    def answer_article_question(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: list[tuple[str, str]],
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.answer_calls.append(
            (article_title, article_text, question, current_datetime, list(chat_history), list(search_results))
        )
        index = min(len(self.answer_calls) - 1, len(self.answers) - 1)
        return self.answers[index]


class FakeBriefLLM:
    def __init__(self, report: str = "# Brief\n\nGenerated report") -> None:
        self.report = report
        self.shorten_calls: list[tuple[str, str, int]] = []
        self.report_calls: list[tuple[str, str, int]] = []

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        return None

    def shorten_brief_notes(
        self,
        system_prompt: str,
        notes: str,
        *,
        max_tokens: int,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.shorten_calls.append((system_prompt, notes, max_tokens))
        return "\n".join(f"- Short note [{number}]" for number in _source_numbers(notes))

    def synthesize_brief_report(
        self,
        system_prompt: str,
        notes: str,
        *,
        max_tokens: int,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        self.report_calls.append((system_prompt, notes, max_tokens))
        return self.report


def _source_numbers(value: str) -> list[int]:
    numbers: list[int] = []
    for part in value.split("[")[1:]:
        raw_number = part.split("]", 1)[0]
        if not raw_number.isdigit():
            continue
        number = int(raw_number)
        if number not in numbers:
            numbers.append(number)
    return numbers or [1]


class FakeExportService:
    def __init__(self, result: ExportResult | None = None) -> None:
        self.result = result or ExportResult(True, "saved png export to exports/test.png")
        self.calls: list[tuple[ExportAction, str, ViewMode, str]] = []

    def export(self, action, *, article, view_mode, theme, config):  # type: ignore[no-untyped-def]
        self.calls.append((action, article.article_id, view_mode, theme.name))
        return self.result
