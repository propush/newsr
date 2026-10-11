from __future__ import annotations

import re
from typing import Final

from .locales import normalize_ui_locale
from .messages_en import EN_MESSAGES
from .messages_ru import RU_MESSAGES

_MESSAGES: Final[dict[str, dict[str, str]]] = {
    "en": EN_MESSAGES,
    "ru": RU_MESSAGES,
}


class UILocalizer:
    _STATUS_PATTERNS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
        (re.compile(r"^fetching (?P<provider>.+): (?P<target>.+)$"), "app.status.fetching_target"),
        (
            re.compile(r"^failed to fetch (?P<provider>.+): (?P<target>.+): (?P<error>.+)$"),
            "app.status.failed_to_fetch_target",
        ),
        (re.compile(r"^extracting (?P<article_id>.+)$"), "app.status.extracting_article"),
        (
            re.compile(r"^classifying (?P<article_id>.+), done (?P<done>\d+) of (?P<total>\d+)$"),
            "app.status.classifying_article",
        ),
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
                r"^Loaded (?P<providers>\d+) providers\. Enabled (?P<enabled>\d+)\. Selected (?P<selected>\d+) targets globally\.$"
            ),
            "source.status.counts",
        ),
    )

    _STATUS_KEYS: Final[dict[str, str]] = {
        "ready": "app.status.ready",
        "refresh already running": "app.status.refresh_already_running",
        "classifying article categories...": "app.status.classifying_current_article",
        "article categories updated": "app.status.article_categories_updated",
        "opened article in browser": "app.status.browser_opened",
        "browser did not confirm open request": "app.status.browser_not_confirmed",
        "no article to export": "app.status.no_article_to_export",
        "checking llm responsiveness...": "app.status.checking_llm",
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
