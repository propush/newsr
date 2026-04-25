from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from threading import Thread
from typing import TYPE_CHECKING

from ...cancellation import RefreshCancellation, RefreshCancelled
from ...providers.search.duckduckgo import SearchResult
from ..screens import ArticleQuestionScreen
from . import article_context_source_text

if TYPE_CHECKING:
    from ...domain import ArticleRecord
    from ..app import NewsReaderApp


@dataclass(slots=True)
class ArticleQuestionTurn:
    turn_id: int
    question: str
    answer: str | None = None
    error_text: str | None = None
    sources: list[SearchResult] = field(default_factory=list)
    pending: bool = False


class ArticleQAController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._screen: ArticleQuestionScreen | None = None
        self._thread: Thread | None = None
        self._cancellation: RefreshCancellation | None = None
        self._article_id: str | None = None
        self._turns: list[ArticleQuestionTurn] = []
        self._turn_ids = count(1)

    @property
    def is_active(self) -> bool:
        return self._screen is not None

    def submit(self, question: str) -> None:
        article = self._app.current_article
        if article is None:
            return
        cleaned_question = question.strip()
        if not cleaned_question or self._cancellation is not None:
            return
        chat_history = self._history()
        turn = ArticleQuestionTurn(
            turn_id=next(self._turn_ids),
            question=cleaned_question,
            pending=True,
        )
        self._turns.append(turn)
        screen = self._ensure_screen(article)
        screen.set_question("")
        self._update_loading_state(article, "asking configured llm for web search query...")
        self._start_request(article, turn.turn_id, cleaned_question, chat_history)

    def close(self) -> None:
        self._cancel_request(clear_turns=True)
        self._dismiss_screen()

    def cancel(self) -> None:
        self._cancel_request(clear_turns=True)

    def open_source(self, index: int) -> None:
        sources = self._visible_sources()
        if index < 0 or index >= len(sources):
            return
        source = sources[index]
        self._app.request_open_link(source.title, source.url)

    def show(self, article: ArticleRecord) -> None:
        self._app.close_more_info()
        screen = self._ensure_screen(article)
        screen.focus_input()

    def _ensure_screen(self, article: ArticleRecord) -> ArticleQuestionScreen:
        existing = self._screen
        if existing is not None:
            if self._article_id != article.article_id:
                self.close()
            else:
                existing.article_title = article.translated_title or article.title
                existing.update_header()
                existing.set_content(self._transcript())
                existing.set_sources(self._source_links())
                return existing
        screen = ArticleQuestionScreen(self._app.ui, article.translated_title or article.title)
        self._screen = screen
        self._article_id = article.article_id
        self._app.push_screen(screen)
        screen.set_content(self._transcript())
        screen.set_sources(self._source_links())
        return screen

    def _start_request(
        self,
        article: ArticleRecord,
        turn_id: int,
        question: str,
        chat_history: list[tuple[str, str]],
    ) -> None:
        self._cancel_request(clear_turns=False)
        cancellation = RefreshCancellation()
        self._cancellation = cancellation
        self._article_id = article.article_id
        self._thread = Thread(
            target=self._run_request,
            args=(article, turn_id, question, chat_history, cancellation),
            name="newsr-article-qa",
            daemon=True,
        )
        self._thread.start()

    def _run_request(
        self,
        article: ArticleRecord,
        turn_id: int,
        question: str,
        chat_history: list[tuple[str, str]],
        cancellation: RefreshCancellation,
    ) -> None:
        current_datetime = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        try:
            original_article_title = article.title
            original_article_text = article_context_source_text(article)
            self._schedule_progress(article, cancellation, "asking configured llm for web search query...")
            query = self._app.llm_client.build_article_question_query(
                original_article_title,
                original_article_text,
                question,
                current_datetime,
                chat_history,
                cancellation,
            ).strip()
            if not query:
                query = original_article_title
            self._schedule_progress(article, cancellation, "searching DuckDuckGo...")
            results = self._app.search_client.search(query, cancellation=cancellation)
            self._schedule_progress(article, cancellation, "asking configured llm to answer...")
            answer = self._app.llm_client.answer_article_question(
                original_article_title,
                original_article_text,
                question,
                current_datetime,
                chat_history,
                results,
                cancellation,
            )
        except RefreshCancelled:
            return
        except Exception as exc:
            if self._app.is_mounted:
                self._app.call_from_thread(
                    self._finish_error,
                    article.article_id,
                    turn_id,
                    cancellation,
                    str(exc),
                )
            return
        if self._app.is_mounted:
            self._app.call_from_thread(
                self._finish_success,
                article.article_id,
                turn_id,
                cancellation,
                answer,
                results,
            )

    def _finish_success(
        self,
        article_id: str,
        turn_id: int,
        cancellation: RefreshCancellation,
        answer: str,
        sources: list[SearchResult],
    ) -> None:
        if cancellation is not self._cancellation or article_id != self._article_id:
            return
        self._thread = None
        self._cancellation = None
        turn = self._find_turn(turn_id)
        if turn is None:
            return
        turn.pending = False
        turn.answer = answer
        turn.sources = list(sources)
        if self._screen is not None:
            self._screen.set_loading(False)
            self._screen.set_status("ready")
            self._screen.set_content(self._transcript())
            self._screen.set_sources(self._source_links())
            self._screen.focus_input()

    def _finish_error(
        self,
        article_id: str,
        turn_id: int,
        cancellation: RefreshCancellation,
        error_text: str,
    ) -> None:
        if cancellation is not self._cancellation or article_id != self._article_id:
            return
        self._thread = None
        self._cancellation = None
        turn = self._find_turn(turn_id)
        if turn is None:
            return
        turn.pending = False
        turn.error_text = error_text
        if self._screen is not None:
            self._screen.set_loading(False)
            self._screen.set_status("failed")
            self._screen.set_content(self._transcript())
            self._screen.set_sources(self._source_links())
            self._screen.focus_input()

    def _cancel_request(self, *, clear_turns: bool) -> None:
        cancellation = self._cancellation
        self._cancellation = None
        self._thread = None
        if cancellation is not None:
            cancellation.cancel()
        if clear_turns:
            self._turns = []

    def _dismiss_screen(self) -> None:
        from textual.app import ScreenStackError

        screen = self._screen
        self._screen = None
        self._article_id = None
        if screen is None:
            return
        try:
            screen.dismiss()
        except ScreenStackError:
            pass
        self._app.restore_reader_focus()

    def _schedule_progress(
        self,
        article: ArticleRecord,
        cancellation: RefreshCancellation,
        stage: str,
    ) -> None:
        if self._app.is_mounted:
            self._app.call_from_thread(self._handle_progress, article, cancellation, stage)

    def _handle_progress(
        self,
        article: ArticleRecord,
        cancellation: RefreshCancellation,
        stage: str,
    ) -> None:
        if cancellation is not self._cancellation or article.article_id != self._article_id:
            return
        self._update_loading_state(article, stage)

    def _update_loading_state(self, article: ArticleRecord, stage: str) -> None:
        screen = self._ensure_screen(article)
        screen.set_loading(True)
        screen.set_status(stage)
        screen.set_content(self._transcript())
        screen.set_sources(self._source_links())

    def _transcript(self) -> str:
        ui = self._app.ui
        if not self._turns:
            return ui.text("article_qa.transcript.empty")
        sections = [ui.text("article_qa.transcript.title")]
        for index, turn in enumerate(self._turns, start=1):
            sections.append(ui.text("article_qa.transcript.question", index=index, question=turn.question))
            if turn.pending:
                sections.append(ui.text("article_qa.transcript.pending"))
                continue
            if turn.error_text is not None:
                sections.append(ui.text("article_qa.transcript.answer_unavailable", error=turn.error_text))
                continue
            sections.append(
                ui.text(
                    "article_qa.transcript.answer",
                    answer=turn.answer or ui.text("article_qa.transcript.no_answer"),
                )
            )
            sections.append(self._sources_markdown(turn.sources))
        return "\n\n".join(sections)

    def _sources_markdown(self, sources: list[SearchResult]) -> str:
        ui = self._app.ui
        if not sources:
            return ui.text("article_qa.transcript.sources_empty")
        lines = [ui.text("article_qa.transcript.sources_title")]
        for index, source in enumerate(sources, start=1):
            lines.append(f"{index}. [{source.title}]({source.url})")
        return "\n".join(lines)

    def _history(self) -> list[tuple[str, str]]:
        return [
            (turn.question, turn.answer or "")
            for turn in self._answered_turns()
        ]

    def _answered_turns(self) -> list[ArticleQuestionTurn]:
        return [
            turn
            for turn in self._turns
            if not turn.pending and turn.answer is not None and turn.error_text is None
        ]

    def _find_turn(self, turn_id: int) -> ArticleQuestionTurn | None:
        for turn in self._turns:
            if turn.turn_id == turn_id:
                return turn
        return None

    def _visible_sources(self) -> list[SearchResult]:
        for turn in reversed(self._turns):
            if turn.pending or turn.error_text is not None:
                continue
            return turn.sources
        return []

    def _source_links(self) -> list[tuple[str, str]]:
        return [(source.title, source.url) for source in self._visible_sources()]
