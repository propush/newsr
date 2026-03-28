from __future__ import annotations

import locale
import os
import re
from dataclasses import dataclass
from typing import Final


DEFAULT_UI_LOCALE = "en"


@dataclass(frozen=True, slots=True)
class UILocaleDefinition:
    code: str
    name: str
    aliases: tuple[str, ...] = ()


PREDEFINED_UI_LOCALES: Final[tuple[UILocaleDefinition, ...]] = (
    UILocaleDefinition("en", "English", aliases=("english",)),
)


_LOCALE_BY_CODE: Final[dict[str, UILocaleDefinition]] = {
    locale.code: locale
    for locale in PREDEFINED_UI_LOCALES
}

_LOCALE_BY_ALIAS: Final[dict[str, str]] = {
    alias: locale.code
    for locale in PREDEFINED_UI_LOCALES
    for alias in (locale.code, locale.name.lower(), *locale.aliases)
}

_MESSAGES: Final[dict[str, dict[str, str]]] = {
    "en": {
        "app.binding.previous": "Previous",
        "app.binding.next": "Next",
        "app.binding.up": "Up",
        "app.binding.down": "Down",
        "app.binding.pgup": "PgUp",
        "app.binding.pgdn": "PgDn",
        "app.binding.back": "Back",
        "app.binding.space": "Space",
        "app.binding.summary": "Summary",
        "app.binding.more_info": "More Info",
        "app.binding.ask": "Ask",
        "app.binding.list": "List",
        "app.binding.sources": "Sources",
        "app.binding.export": "Export",
        "app.binding.open": "Open",
        "app.binding.download": "Download",
        "app.binding.help": "Help",
        "app.binding.quit": "Quit",
        "app.empty.header": "No cached articles",
        "app.empty.body": "Press D to fetch articles.",
        "app.article.position": "Article # {current} of {total}",
        "app.article.date": "Date : {date}",
        "app.article.title": "Title: {title}",
        "app.article.mode": "Mode : {mode}",
        "app.article.mode.full": "full",
        "app.article.mode.summary": "summary",
        "app.article.url": "URL: {url}",
        "app.status.ready": "ready",
        "app.status.refresh_already_running": "refresh already running",
        "app.status.fetching_target": "fetching {provider}: {target}",
        "app.status.failed_to_fetch_target": "failed to fetch {provider}: {target}: {error}",
        "app.status.extracting_article": "extracting {article_id}",
        "app.status.translating_article": "translating {article_id}, done {done} of {total}",
        "app.status.summarizing_article": "summarizing {article_id}, done {done} of {total}",
        "app.status.browser_open_failed": "failed to open browser: {error}",
        "app.status.browser_opened": "opened article in browser",
        "app.status.browser_not_confirmed": "browser did not confirm open request",
        "app.status.no_article_to_export": "no article to export",
        "app.status.exiting": "Exiting...",
        "app.status.sources_unchanged": "sources unchanged",
        "app.status.sources_saved_next_refresh": "sources saved; next refresh will use updated provider settings",
        "app.status.sources_saved_refreshing": "sources saved; refreshing enabled providers",
        "help.body": (
            "Left/Right: previous/next article\n"
            "Up/Down/PgUp/PgDn/B: scroll\n"
            "Space: page down or next article\n"
            "S: toggle summary\n"
            "M: more info\n"
            "?: ask about article\n"
            "L: article list\n"
            "C: sources\n"
            "E: export current view\n"
            "O: open article in browser\n"
            "D: download new articles\n"
            "Ctrl+P: command palette / choose theme\n"
            "H: help\n"
            "Q: quit"
        ),
        "source.binding.close": "Close",
        "source.binding.pane": "Pane",
        "source.binding.toggle": "Toggle",
        "source.binding.refresh": "Refresh",
        "source.binding.apply": "Apply",
        "source.header": "Manage Sources",
        "source.loading.status": "Loading providers and targets...",
        "source.loading.body": "Loading sources...",
        "source.hint": "Tab: switch pane   Space: toggle   R: refresh catalog   A: apply   Esc: close",
        "source.status.still_loading": "Sources are still loading.",
        "source.status.refreshing_catalog": "Refreshing {provider} catalog...",
        "source.status.failed_load": "Failed to load sources: {error}",
        "source.status.failed_refresh": "Failed to refresh sources: {error}",
        "source.status.refreshed_catalog": "Refreshed {provider} catalog.",
        "source.status.unable_to_load": "Unable to load sources.",
        "source.status.counts": "Loaded {providers} providers. Enabled {enabled}. Selected {selected} targets.",
        "source.table.provider": "Provider",
        "source.table.targets": "Targets",
        "source.table.target": "Target",
        "article_qa.binding.close": "Close",
        "article_qa.binding.next": "Next",
        "article_qa.binding.previous": "Previous",
        "article_qa.binding.pgup": "PgUp",
        "article_qa.binding.pgdn": "PgDn",
        "article_qa.label.sources": "Sources",
        "article_qa.placeholder": "Ask anything about this article",
        "article_qa.hint": "Enter: ask/open source   Tab: input/sources   Esc: close   PgUp/PgDn: scroll answer",
        "article_qa.header": "Ask About This Article\nTitle: {title}\nState: {state}",
        "article_qa.transcript.empty": (
            "# Article Q&A\n\n"
            "Ask anything about this article in any language.\n\n"
            "Answers use the original article text plus live DuckDuckGo results.\n\n"
            "Nothing in this chat is saved after you close the modal."
        ),
        "article_qa.transcript.title": "# Article Q&A",
        "article_qa.transcript.question": "## Question {index}\n\n**You:** {question}",
        "article_qa.transcript.pending": "_Searching the web and drafting an answer..._",
        "article_qa.transcript.answer_unavailable": (
            "### Answer unavailable\n\n"
            "The question could not be answered right now.\n\n"
            "Error: `{error}`"
        ),
        "article_qa.transcript.answer": "### Answer\n\n{answer}",
        "article_qa.transcript.no_answer": "_No answer returned._",
        "article_qa.transcript.sources_title": "### Sources",
        "article_qa.transcript.sources_empty": "### Sources\n\n_No public search results were found for this question._",
        "more_info.binding.close": "Close",
        "more_info.binding.refresh": "Refresh",
        "more_info.binding.previous": "Previous",
        "more_info.binding.next": "Next",
        "more_info.binding.back": "Back",
        "more_info.binding.space": "Space",
        "more_info.hint": "Esc: close   Space/B: page   M: refresh   Left/Right: change article",
        "more_info.header": "More Info\nTitle: {title}\nState: {state}",
        "more_info.body.unavailable": "# More info unavailable\n\nThe additional lookup failed.\n\nError: `{error}`",
        "more_info.body.no_results": "No additional public context was found for this article yet.",
        "more_info.body.loading": "# More Info\n\nGathering extra context for:\n\n**{title}**\n\nCurrent step: {stage}",
        "quick_nav.binding.close": "Close",
        "quick_nav.header": "Quick Navigation",
        "quick_nav.empty": "No translated articles available.",
        "quick_nav.hint": "Up/Down: select   Enter: open article   Esc: close",
        "quick_nav.selection": "Selected {current} of {total}",
        "quick_nav.table.date": "Date",
        "quick_nav.table.title": "Title",
        "quick_nav.table.provider": "Provider",
        "quick_nav.table.category": "Category",
        "export.binding.save_png": "Save PNG",
        "export.binding.copy_png": "Copy PNG",
        "export.binding.save_markdown": "Save MD",
        "export.binding.copy_markdown": "Copy MD",
        "export.binding.cancel": "Cancel",
        "export.header": "Export Current View",
        "export.body": (
            "Title: {title}\n"
            "Mode: {mode}\n\n"
            "1: Save PNG   2: Copy PNG\n"
            "3: Save Markdown   4: Copy Markdown"
        ),
        "export.button.save_png": "Save PNG",
        "export.button.copy_png": "Copy PNG",
        "export.button.save_markdown": "Save Markdown",
        "export.button.copy_markdown": "Copy Markdown",
        "export.button.cancel": "Cancel",
        "open_link.binding.open": "Open",
        "open_link.binding.cancel": "Cancel",
        "open_link.header": "Open Source Link",
        "open_link.source_link": "Source link",
        "open_link.body": "Open this source in your browser?\n\nTitle: {title}\nURL: {url}",
        "open_link.button.open": "Open",
        "open_link.button.cancel": "Cancel",
        "status.loading": "loading...",
        "status.cached": "cached",
        "status.failed": "failed",
        "status.asking_search_query": "asking configured llm for search query...",
        "status.searching_duckduckgo": "searching DuckDuckGo...",
        "status.synthesizing_results": "asking configured llm to synthesize results...",
        "status.asking_web_search_query": "asking configured llm for web search query...",
        "status.asking_llm_to_answer": "asking configured llm to answer...",
    }
}


def available_ui_locale_names() -> tuple[str, ...]:
    return tuple(locale.name for locale in PREDEFINED_UI_LOCALES)


def resolve_ui_locale_name(value: str) -> str:
    locale_code = normalize_ui_locale(value)
    return _LOCALE_BY_CODE[locale_code].name


def normalize_ui_locale(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return DEFAULT_UI_LOCALE
    return _LOCALE_BY_ALIAS.get(normalized, DEFAULT_UI_LOCALE)


def parse_ui_locale(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    return _LOCALE_BY_ALIAS.get(normalized)


def guess_ui_locale(locale_name: str | None = None) -> str:
    resolved_locale = locale_name or _detect_locale_name()
    if not resolved_locale:
        return DEFAULT_UI_LOCALE
    normalized_locale = resolved_locale.split(".", 1)[0].split("@", 1)[0]
    language_code = normalized_locale.replace("-", "_").split("_", 1)[0].lower()
    if language_code in _LOCALE_BY_CODE:
        return language_code
    return DEFAULT_UI_LOCALE


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


class UILocalizer:
    _STATUS_PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
        (re.compile(r"^fetching (?P<provider>.+): (?P<target>.+)$"), "app.status.fetching_target"),
        (
            re.compile(r"^failed to fetch (?P<provider>.+): (?P<target>.+): (?P<error>.+)$"),
            "app.status.failed_to_fetch_target",
        ),
        (re.compile(r"^extracting (?P<article_id>.+)$"), "app.status.extracting_article"),
        (
            re.compile(r"^translating (?P<article_id>.+), done (?P<done>\d+) of (?P<total>\d+)$"),
            "app.status.translating_article",
        ),
        (
            re.compile(r"^summarizing (?P<article_id>.+), done (?P<done>\d+) of (?P<total>\d+)$"),
            "app.status.summarizing_article",
        ),
        (re.compile(r"^failed to open browser: (?P<error>.+)$"), "app.status.browser_open_failed"),
        (re.compile(r"^Refreshing (?P<provider>.+) catalog\.\.\.$"), "source.status.refreshing_catalog"),
        (re.compile(r"^Failed to load sources: (?P<error>.+)$"), "source.status.failed_load"),
        (re.compile(r"^Failed to refresh sources: (?P<error>.+)$"), "source.status.failed_refresh"),
        (re.compile(r"^Refreshed (?P<provider>.+) catalog\.$"), "source.status.refreshed_catalog"),
        (
            re.compile(
                r"^Loaded (?P<providers>\d+) providers\. Enabled (?P<enabled>\d+)\. Selected (?P<selected>\d+) targets\.$"
            ),
            "source.status.counts",
        ),
    )

    _STATUS_KEYS: Final[dict[str, str]] = {
        "ready": "app.status.ready",
        "refresh already running": "app.status.refresh_already_running",
        "opened article in browser": "app.status.browser_opened",
        "browser did not confirm open request": "app.status.browser_not_confirmed",
        "no article to export": "app.status.no_article_to_export",
        "Exiting...": "app.status.exiting",
        "sources unchanged": "app.status.sources_unchanged",
        "sources saved; next refresh will use updated provider settings": "app.status.sources_saved_next_refresh",
        "sources saved; refreshing enabled providers": "app.status.sources_saved_refreshing",
        "Sources are still loading.": "source.status.still_loading",
        "Unable to load sources.": "source.status.unable_to_load",
        "loading...": "status.loading",
        "cached": "status.cached",
        "failed": "status.failed",
        "asking configured llm for search query...": "status.asking_search_query",
        "searching DuckDuckGo...": "status.searching_duckduckgo",
        "asking configured llm to synthesize results...": "status.synthesizing_results",
        "asking configured llm for web search query...": "status.asking_web_search_query",
        "asking configured llm to answer...": "status.asking_llm_to_answer",
    }

    def __init__(self, locale_code: str) -> None:
        self.locale = normalize_ui_locale(locale_code)
        self._messages = _MESSAGES[self.locale]

    def text(self, key: str, **kwargs: object) -> str:
        template = self._messages[key]
        return template.format(**kwargs) if kwargs else template

    def status(self, value: str) -> str:
        key = self._STATUS_KEYS.get(value)
        if key is not None:
            return self.text(key)
        for pattern, pattern_key in self._STATUS_PATTERNS:
            match = pattern.match(value)
            if match is not None:
                return self.text(pattern_key, **match.groupdict())
        return value
