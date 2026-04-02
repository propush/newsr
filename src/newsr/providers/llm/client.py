from __future__ import annotations

import http.client
import json
import logging
from itertools import count
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Sequence
from urllib.parse import urlparse

from ...domain.article_categories import ARTICLE_CATEGORIES, normalize_article_categories
from ...cancellation import RefreshCancellation, cancellable_read
from ...config.models import AppConfig
from ..search.duckduckgo import SearchResult


LOGGER = logging.getLogger("newsr.llm")
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


def _configure_logger() -> None:
    if LOGGER.handlers:
        return
    log_path = Path.cwd() / "cache" / "newsr-llm.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)


class OpenAILLMClient:
    def __init__(self, config: AppConfig) -> None:
        _configure_logger()
        self.base_url = config.llm.url
        self.target_language = config.translation.target_language
        self.translation_model = config.llm.model_translation
        self.summary_model = config.llm.model_summary
        self.api_key = config.llm.api_key
        self.extra_headers = dict(config.llm.headers or {})
        self.request_retries = config.llm.request_retries
        self._request_ids = count(1)
        self._slot_lock = Lock()
        self._conn: http.client.HTTPConnection | http.client.HTTPSConnection | None = None
        parsed = urlparse(self.base_url)
        self._scheme = (parsed.scheme or "http").lower()
        self._host = parsed.hostname or "localhost"
        self._port = parsed.port or (443 if self._scheme == "https" else 80)
        self._path_prefix = (parsed.path or "").rstrip("/")

    def translate(
        self,
        article_title: str,
        source_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        prompt = (
            f"Translate the following news article into {self.target_language}. "
            f"Article headline: '{article_title}'. "
            "Translate the COMPLETE text from start to finish — do not skip, summarize, or truncate any part. "
            "Preserve the factual meaning and paragraph structure. "
            "Use light markdown only when it improves readability. "
            "Return only the translated text with no commentary."
        )
        return self._chat(self.translation_model, prompt, source_text, cancellation)

    def translate_title(
        self, article_title: str, cancellation: RefreshCancellation | None = None
    ) -> str:
        prompt = (
            f"Translate the news headline into {self.target_language}. "
            "Return only the translated headline without commentary or quotes."
        )
        return self._chat(self.translation_model, prompt, article_title, cancellation)

    def check_responsive(self, cancellation: RefreshCancellation | None = None) -> None:
        response = self._chat(
            self.translation_model,
            "Reply with OK only.",
            "ping",
            cancellation,
        )
        if not response.strip():
            raise RuntimeError("LLM returned an empty response")

    def summarize(
        self,
        article_title: str,
        translated_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        prompt = (
            f"Summarize the article '{article_title}' in {self.target_language}. "
            "Return a concise, readable summary with the main facts only. "
            "Use short paragraphs and occasional bullet points only when helpful."
        )
        return self._chat(self.summary_model, prompt, translated_text, cancellation)

    def classify_article_categories(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> tuple[str, ...]:
        category_list = ", ".join(ARTICLE_CATEGORIES)
        prompt = (
            f"Classify the news article '{article_title}' using only these labels: {category_list}. "
            "Return a JSON array with at least one label. "
            "Use only exact labels from the allowed list. "
            "Do not add commentary."
        )
        remaining_attempts = self.request_retries + 1
        while remaining_attempts > 0:
            raw = self._chat(
                self.translation_model,
                prompt,
                f"{article_title}\n\n{article_text}",
                cancellation,
            )
            categories = _parse_category_response(raw)
            if categories:
                return categories
            remaining_attempts -= 1
            if remaining_attempts == 0:
                return ()
            LOGGER.warning(
                "classification_empty_result title=%r attempts_remaining=%s",
                article_title,
                remaining_attempts,
            )
        return ()

    def build_search_query(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        prompt = (
            "Write a short DuckDuckGo web search query for this news article using its original language. "
            "Use the main subject, key people, place, and event terms when available. "
            "Return only the query text with no quotes or commentary."
        )
        return self._chat(self.summary_model, prompt, f"{article_title}\n\n{article_text}", cancellation)

    def extract_watch_topic(
        self,
        article_title: str,
        article_text: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        prompt = (
            "Extract a short topic name for creating a persistent news watch from this article. "
            "Return only the topic name, 2 to 6 words when possible, with no quotes or commentary."
        )
        return self._chat(self.summary_model, prompt, f"{article_title}\n\n{article_text}", cancellation).strip()

    def synthesize_more_info(
        self,
        article_title: str,
        article_text: str,
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        results_text = "\n\n".join(
            (
                f"Result {index}: {result.title}\n"
                f"URL: {result.url}\n"
                f"Snippet: {result.snippet}"
            )
            for index, result in enumerate(search_results, start=1)
        )
        prompt = (
            f"You are writing a 'more info' panel for the news article '{article_title}' "
            f"in {self.target_language}. "
            "The search results are in the article's original language; translate and synthesize them into the target language. "
            "Use only the supplied search results. "
            "Return concise Markdown with a short overview, important added context, and why it matters. "
            "If the search results are thin or uncertain, say so plainly."
        )
        content = f"Article context:\n{article_text}\n\nSearch results:\n{results_text}"
        return self._chat(self.summary_model, prompt, content, cancellation)

    def build_article_question_query(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: Sequence[tuple[str, str]],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        prompt = (
            "Write a short DuckDuckGo web search query for answering a reader question about a news article. "
            "Infer the article's original language from the supplied article context and write the query in that same language. "
            "The user question may be in any language or informal form, so normalize it into a useful public-web query. "
            "Use the article's key people, places, event terms, and the user's question intent. "
            "Current local date and time: "
            f"{current_datetime}. "
            "Return only the query text with no quotes or commentary."
        )
        content = (
            f"Article title:\n{article_title}\n\n"
            f"Article context:\n{article_text}\n\n"
            f"Prior chat turns:\n{self._format_chat_history(chat_history)}\n\n"
            f"Reader question:\n{question}"
        )
        return self._chat(self.summary_model, prompt, content, cancellation)

    def answer_article_question(
        self,
        article_title: str,
        article_text: str,
        question: str,
        current_datetime: str,
        chat_history: Sequence[tuple[str, str]],
        search_results: list[SearchResult],
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        results_text = "\n\n".join(
            (
                f"Result {index}: {result.title}\n"
                f"URL: {result.url}\n"
                f"Snippet: {result.snippet}"
            )
            for index, result in enumerate(search_results, start=1)
        )
        prompt = (
            f"You answer reader questions about the news article '{article_title}' in {self.target_language}. "
            "The article context is in the article's original language and should be treated as the main context. "
            "The reader question may be in any language or form. "
            f"Current local date and time: {current_datetime}. "
            "Use the supplied web search results when they add current or public context, and say plainly when the search support is thin or uncertain. "
            "Return concise Markdown with a direct answer first. "
            "Do not include a sources list in the answer body."
        )
        content = (
            f"Article context:\n{article_text}\n\n"
            f"Prior chat turns:\n{self._format_chat_history(chat_history)}\n\n"
            f"Reader question:\n{question}\n\n"
            f"Search results:\n{results_text or 'No search results were found.'}"
        )
        return self._chat(self.summary_model, prompt, content, cancellation)

    def _ensure_connection(self) -> http.client.HTTPConnection | http.client.HTTPSConnection:
        if self._conn is None:
            connection_class = (
                http.client.HTTPSConnection if self._scheme == "https" else http.client.HTTPConnection
            )
            self._conn = connection_class(self._host, self._port, timeout=300)
        return self._conn

    def _reset_connection(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def _chat(
        self,
        model: str,
        system_prompt: str,
        content: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        with self._slot_lock:
            return self._chat_locked(model, system_prompt, content, cancellation)

    def _chat_locked(
        self,
        model: str,
        system_prompt: str,
        content: str,
        cancellation: RefreshCancellation | None = None,
    ) -> str:
        request_id = next(self._request_ids)
        payload = json.dumps(
            {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
            }
        ).encode("utf-8")

        started_at = perf_counter()
        LOGGER.info(
            "request_start id=%s model=%s prompt_chars=%s content_chars=%s",
            request_id,
            model,
            len(system_prompt),
            len(content),
        )

        try:
            if cancellation is not None:
                cancellation.raise_if_cancelled()
            response = self._perform_request(payload, cancellation)
            raw = json.loads(cancellable_read(response, cancellation).decode("utf-8"))
            if response.status >= 400:
                message = _extract_error_message(raw)
                raise RuntimeError(f"LLM request failed with HTTP {response.status}: {message}")
            text = str(raw["choices"][0]["message"]["content"]).strip()
            LOGGER.info(
                "request_done id=%s model=%s duration_s=%.3f response_chars=%s",
                request_id,
                model,
                perf_counter() - started_at,
                len(text),
            )
            return text
        except Exception:
            self._reset_connection()
            LOGGER.exception(
                "request_failed id=%s model=%s duration_s=%.3f",
                request_id,
                model,
                perf_counter() - started_at,
            )
            raise

    def _perform_request(
        self,
        payload: bytes,
        cancellation: RefreshCancellation | None,
    ) -> http.client.HTTPResponse:
        remaining_attempts = self.request_retries + 1
        last_error: Exception | None = None
        while remaining_attempts > 0:
            if cancellation is not None:
                cancellation.raise_if_cancelled()
            conn = self._ensure_connection()
            try:
                conn.request(
                    "POST",
                    f"{self._path_prefix}/chat/completions",
                    body=payload,
                    headers=self._request_headers(),
                )
                return conn.getresponse()
            except (http.client.RemoteDisconnected, ConnectionError, OSError) as exc:
                last_error = exc
                remaining_attempts -= 1
                self._reset_connection()
                if remaining_attempts == 0:
                    raise
        raise RuntimeError("LLM request failed without a captured transport error") from last_error

    def _request_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        return headers

    @staticmethod
    def _format_chat_history(chat_history: Sequence[tuple[str, str]]) -> str:
        if not chat_history:
            return "No prior chat turns."
        return "\n\n".join(
            f"Question {index}: {question}\nAnswer {index}: {answer}"
            for index, (question, answer) in enumerate(chat_history, start=1)
        )


def _extract_error_message(raw: object) -> str:
    if isinstance(raw, dict):
        error = raw.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
    return "Unknown error"


def _parse_category_response(raw: str) -> tuple[str, ...]:
    stripped = raw.strip()
    if stripped == "[]":
        return ()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return normalize_article_categories(_extract_category_tokens(stripped))
    if not isinstance(parsed, list):
        return ()
    return normalize_article_categories(item for item in parsed if isinstance(item, str))


def _extract_category_tokens(raw: str) -> list[str]:
    return [
        token.strip()
        for token in raw.replace("\n", ",").split(",")
        if token.strip()
    ]
