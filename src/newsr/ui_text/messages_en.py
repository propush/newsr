from __future__ import annotations

from typing import Final

EN_MESSAGES: Final[dict[str, str]] = {
    "app.binding.previous": "Previous",
    "app.binding.next": "Next",
    "app.binding.up": "Up",
    "app.binding.down": "Down",
    "app.binding.pgup": "PgUp",
    "app.binding.pgdn": "PgDn",
    "app.binding.back": "Back",
    "app.binding.classify": "Classify",
    "app.binding.space": "Space",
    "app.binding.mode": "Mode",
    "app.binding.more_info": "More Info",
    "app.binding.ask": "Ask",
    "app.binding.list": "List",
    "app.binding.sources": "Sources",
    "app.binding.export": "Export",
    "app.binding.open": "Open",
    "app.binding.search_check": "Open DuckDuckGo Check",
    "app.binding.watch_topic": "Watch Topic",
    "app.binding.download": "Refresh",
    "app.binding.brief": "Brief Review",
    "app.binding.help": "Help",
    "app.binding.providers": "Providers",
    "app.binding.quit": "Quit",
    "app.binding.playlist_add": "Add to Playlist",
    "app.binding.playlist_add_rest": "Add Rest to Playlist",
    "app.binding.play_pause": "Play/Pause",
    "app.binding.playlist": "Playlist",
    "app.binding.playlist_skip": "Next in Playlist",
    "app.binding.playlist_previous": "Previous Article",
    "app.binding.playlist_seek_forward": "Forward One Passage",
    "app.binding.playlist_seek_back": "Back One Passage",
    "clipboard.error": "Native clipboard unavailable: {error}. Terminal clipboard copy was also requested.",
    "app.empty.header": "No cached articles",
    "app.empty.body": "Press D to fetch articles.",
    "app.article.position": "Article # {current} of {total}",
    "app.article.date": "Date : {date}",
    "app.article.title": "Title: {title}",
    "app.article.mode": "Mode : {mode}",
    "app.article.mode.full": "full",
    "app.article.mode.summary": "summary",
    "app.article.mode.original": "original",
    "app.article.url": "URL: {url}",
    "app.status.ready": "ready",
    "app.status.refresh_already_running": "refresh already running",
    "app.status.fetching_target": "fetching {provider}: {target}",
    "app.status.failed_to_fetch_target": "failed to fetch {provider}: {target}: {error}",
    "app.status.extracting_article": "extracting {article_id}",
    "app.status.classifying_article": "classifying {article_id}, done {done} of {total}",
    "app.status.translating_article": "translating {article_id}, done {done} of {total}",
    "app.status.summarizing_article": "summarizing {article_id}, done {done} of {total}",
    "app.status.classifying_current_article": "classifying article categories...",
    "app.status.article_categories_updated": "article categories updated",
    "app.status.article_categories_update_failed": "failed to classify article categories: {error}",
    "app.status.browser_open_failed": "failed to open browser: {error}",
    "app.status.browser_opened": "opened article in browser",
    "app.status.browser_not_confirmed": "browser did not confirm open request",
    "search_check.title": "DuckDuckGo check",
    "search_check.notice": "DuckDuckGo asks for a browser check. Press Ctrl+O to open it in your browser, then retry the search.",
    "search_check.status.none": "no pending DuckDuckGo check",
    "search_check.status.opened": "opened DuckDuckGo check in browser",
    "app.status.no_article_to_export": "no article to export",
    "app.status.checking_llm": "checking llm responsiveness...",
    "app.status.exiting": "Exiting...",
    "app.status.sources_unchanged": "sources unchanged",
    "app.status.sources_saved": "sources saved",
    "app.status.sources_saved_next_refresh": "sources saved; next refresh will use updated provider settings",
    "app.status.sources_saved_refreshing": "sources saved; refreshing enabled providers",
    "confirm_dialog.llm_unresponsive.header": "LLM Unavailable",
    "confirm_dialog.llm_unresponsive.body": "LLM is not responsive: {error}. Try again?",
    "confirm_dialog.button.retry": "Retry",
    "confirm_dialog.button.cancel": "Cancel",
    "help.body.reader": (
        "Ctrl+C: copy selected text (also in macOS Terminal)\n"
        "Cmd+C / Ctrl+Shift+C: copy when forwarded by the terminal\n"
        "Left/Right: previous/next article\n"
        "Up/Down/PgUp/PgDn/B: scroll\n"
        "K: classify categories\n"
        "Space: page down or next article\n"
        "S: cycle reader mode\n"
        "M: more info\n"
        "?: ask about article\n"
        "L: article list\n"
        "A: add article to playlist\n"
        "Shift+A: add this and following articles to playlist\n"
        "P: play/pause playlist\n"
        "Shift+P: show playlist\n"
        "] / [: next playlist article / restart current article, at its start the previous one\n"
        ". / ,: playlist forward / back one passage\n"
        "Esc: back to providers\n"
        "C: sources\n"
        "W: watch topic\n"
        "E: export current view\n"
        "O: open article in browser\n"
        "Ctrl+O: open pending DuckDuckGo browser check\n"
        "D: force refresh current provider\n"
        "Ctrl+P: command palette / choose theme\n"
        "H: help\n"
        "Q: quit"
    ),
    "help.body.provider_home": (
        "Ctrl+C: copy selected text (also in macOS Terminal)\n"
        "Cmd+C / Ctrl+Shift+C: copy when forwarded by the terminal\n"
        "Up/Down/PgUp/PgDn: move through providers\n"
        "Enter/Space: open the selected provider\n"
        "B: brief review\n"
        "C: manage sources\n"
        "W: create watched topic\n"
        "D: force refresh all providers\n"
        "P: play/pause playlist\n"
        "Shift+P: show playlist\n"
        "] / [: next playlist article / restart current article, at its start the previous one\n"
        ". / ,: playlist forward / back one passage\n"
        "Ctrl+O: open pending DuckDuckGo browser check\n"
        "Ctrl+P: command palette / choose theme\n"
        "H: help\n"
        "Q: quit"
    ),
    "provider_home.empty": "No enabled providers. Press C to manage sources.",
    "provider_home.hint": "Up/Down: select   Enter/Space: open provider   B: brief   C: sources   W: watch topic   D: refresh",
    "provider_home.status.empty": "No provider is available.",
    "provider_home.status.selection": "{provider}: {unread} unread, {total} total",
    "provider_home.table.provider": "Provider",
    "provider_home.table.unread": "Unread",
    "provider_home.table.total": "Total",
    "provider_group.virtual": "Virtual",
    "provider_group.providers": "Providers",
    "provider_group.topics": "Topics",
    "source.binding.close": "Close",
    "source.binding.pane": "Pane",
    "source.binding.toggle": "Toggle",
    "source.binding.refresh": "Refresh",
    "source.binding.schedule": "Schedule",
    "source.binding.delete": "Delete",
    "source.binding.apply": "Apply",
    "source.header": "Manage Sources",
    "source.loading.status": "Loading providers and targets...",
    "source.loading.body": "Loading sources...",
    "source.hint": "Space: toggle   U: edit schedule   X: delete topic   A: apply",
    "source.status.still_loading": "Sources are still loading.",
    "source.status.refreshing_catalog": "Refreshing {provider} catalog...",
    "source.status.failed_load": "Failed to load sources: {error}",
    "source.status.failed_refresh": "Failed to refresh sources: {error}",
    "source.status.refreshed_catalog": "Refreshed {provider} catalog.",
    "source.status.unable_to_load": "Unable to load sources.",
    "source.status.counts": "Loaded {providers} providers. Enabled {enabled}. Selected {selected} targets globally.",
    "source.table.provider": "Provider",
    "source.table.type": "Type",
    "source.table.schedule": "Schedule",
    "source.table.target": "Target",
    "source.provider_type.all": "all",
    "source.provider_type.http": "http",
    "source.provider_type.topic": "topic",
    "source.schedule.default": "default",
    "source.schedule.title": "Update Schedule: {provider}",
    "source.schedule.body": (
        "Enter a 5-field cron expression. Leave it blank to use the global default schedule: "
        "{default_schedule}."
    ),
    "source.schedule.placeholder": "Leave blank for {default_schedule}",
    "source.schedule.confirm": "Save",
    "source.schedule.cancel": "Cancel",
    "source.schedule.saved": "Saved update schedule for {provider}.",
    "source.delete.title": "Delete Watched Topic",
    "source.delete.body": "Delete the watched topic provider '{provider}'?",
    "source.delete.confirm": "Delete",
    "source.delete.cancel": "Cancel",
    "source.delete.deleted": "Watched topic deleted.",
    "watch_topic.dialog.title": "Watch Topic",
    "watch_topic.dialog.body": (
        "Choose the topic name and an optional cron schedule override for this watched topic. "
        "Leave the schedule blank to use {default_schedule}."
    ),
    "watch_topic.dialog.topic_placeholder": "Topic name",
    "watch_topic.dialog.schedule_placeholder": "Leave blank for {default_schedule}",
    "watch_topic.dialog.confirm": "Create",
    "watch_topic.dialog.cancel": "Cancel",
    "watch_topic.error.topic_required": "Topic name is required.",
    "watch_topic.error.invalid_schedule": "Invalid cron schedule: {error}",
    "watch_topic.status.extracting": "extracting topic from current article...",
    "watch_topic.status.extract_failed": "failed to extract watch topic: {error}",
    "watch_topic.status.exists": "topic already exists: {topic}",
    "watch_topic.status.created": "created watched topic: {topic}",
    "article_qa.binding.close": "Close",
    "article_qa.binding.next": "Next",
    "article_qa.binding.previous": "Previous",
    "article_qa.binding.pgup": "PgUp",
    "article_qa.binding.pgdn": "PgDn",
    "article_qa.label.sources": "Sources",
    "article_qa.placeholder": "Ask anything about this article",
    "article_qa.hint": (
        "Enter: ask/open source   Up/Down: question history   Tab: input/sources   "
        "Esc: close   PgUp/PgDn: scroll answer"
    ),
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
    "brief.binding.close": "Close",
    "brief.binding.generate": "Generate",
    "brief.header": "Brief Review",
    "brief.period.label": "Period",
    "brief.period.last_24h": "Last 24 hr",
    "brief.period.last_week": "Last week",
    "brief.period.all_unread": "All unread",
    "brief.option.only_unread": "Only unread articles",
    "brief.option.include_topics": "Include watched topics",
    "brief.option.mark_read": "Mark selected sources read",
    "brief.button.generate": "Generate",
    "brief.button.cancel": "Cancel",
    "brief.hint": "Tab/Arrows: move   Enter/Space: toggle or press   G: generate   Esc: cancel/close",
    "brief.body.ready": "# Brief\n\nChoose a period and press Generate.",
    "brief.body.starting": "# Brief\n\nStarting brief generation...",
    "brief.body.generating": "# Brief\n\nGenerating report...\n\nCurrent step: {status}",
    "brief.body.cancelled": "# Brief\n\nGeneration was cancelled.",
    "brief.body.failed": "# Brief unavailable\n\nThe brief could not be generated.\n\nError: `{error}`",
    "brief.status.refresh_busy": "Brief review is unavailable while refresh is running.",
    "brief.status.selecting_articles": "selecting articles",
    "brief.status.marking_read": "marking selected sources read",
    "brief.status.compressing_summaries": "compressing summaries {index} of {total}",
    "brief.status.reducing_notes": "reducing notes pass {pass_number}",
    "brief.status.writing_final": "writing final brief",
    "brief.status.repairing_compressed": (
        "repairing compressed summary batch {batch_index} of {batch_count}, attempt {attempt} of {attempts}"
    ),
    "brief.status.compressed_fallback": "using fallback for compressed summary batch {batch_index} of {batch_count}",
    "brief.status.repairing_final": "repairing final brief, attempt {attempt} of {attempts}",
    "brief.status.final_fallback": "using fallback for final brief",
    "brief_reader.binding.close": "Close",
    "brief_reader.binding.pgup": "PgUp",
    "brief_reader.binding.pgdn": "PgDn",
    "brief_reader.header": "Brief Review",
    "brief_reader.hint": "Esc: close   Up/Down: scroll   Space/B: page",
    "brief_reader.hint_with_jump": "Type number + Enter: open article   Esc: close   Up/Down: scroll",
    "brief_jump.binding.jump": "Jump",
    "brief_jump.binding.cancel": "Cancel",
    "brief_jump.header": "Jump to Article",
    "brief_jump.body": "Enter article number from 1 to {max_number}.",
    "brief_jump.button.jump": "Jump",
    "brief_jump.button.cancel": "Cancel",
    "brief_jump.error.empty": "Enter an article number.",
    "brief_jump.error.number": "Use digits only.",
    "brief_jump.error.range": "Choose a number from 1 to {max_number}.",
    "brief_jump.status.not_found": "brief article is no longer available",
    "playlist.header": "Playlist: {count} articles, {state}",
    "playlist.state.playing": "playing",
    "playlist.state.paused": "paused",
    "playlist.state.stopped": "stopped",
    "playlist.empty": "The playlist is empty. Press A in the reader to add articles.",
    "playlist.hint": "Up/Down: select   Enter: play now   X/Del: remove   C: clear   P/Space: play/pause   ]/[: next/previous   ./,: forward/back   Esc: close",
    "playlist.binding.close": "Close",
    "playlist.binding.play_pause": "Play/Pause",
    "playlist.binding.remove": "Remove",
    "playlist.binding.clear": "Clear",
    "playlist.clear.title": "Clear Playlist",
    "playlist.clear.body": "Remove all {count} articles from the playlist?",
    "playlist.clear.confirm": "Clear",
    "playlist.clear.cancel": "Cancel",
    "playlist.status.empty": "playlist is empty",
    "playlist.status.added": "added {added} to playlist, {total} queued",
    "playlist.status.finished": "playlist finished",
    "playlist.status.playing": "▶ {title} · {provider} · {count} queued",
    "playlist.status.paused": "‖ {title} · {provider} · {count} queued",
    "playlist.status.buffering": "… {title} · {provider} · {count} queued",
    "playlist.status.starting": "… starting playlist, {count} queued",
    "playlist.status.queued": "■ playlist: {count} queued",
    "playlist.status.error": "⚠ TTS: {error}",
    "playlist.speech.intro": "{provider}. Article {current} of {total}.",
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
