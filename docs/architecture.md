# Architecture

NewsR is a single-process local terminal application. It runs from the repository root, keeps its state in SQLite under `cache/`, and uses a provider-backed refresh pipeline to keep the Textual UI responsive while content is fetched and processed.

For the concrete built-in provider list, bootstrap defaults, and catalog behavior, see [Current Providers](current_providers.md). For the current `newsr.yml` schema and defaults, see [Configuration](configuration.md).

## Package Layout

- `newsr.app`: process bootstrap and CLI entrypoint used by `newsr` and `python -m newsr`
- `newsr.config`: config dataclasses plus loading, validation, first-run bootstrap, and `ui.locale` backfill for `newsr.yml`
- `newsr.domain`: shared article, article-category vocabulary, provider, and reader-state models used across UI, storage, and pipeline code
- `newsr.ui_text`: built-in UI locale definitions plus localized labels, prompts, hints, and status text used by both bootstrap and the Textual app
- `newsr.providers.base`: `NewsProvider` protocol used by the refresh pipeline
- `newsr.providers.registry`: built-in provider registration; see [Current Providers](current_providers.md) for the current built-in news provider set
- `newsr.providers.<provider_id>`: built-in provider packages for target discovery, section parsing, article extraction, and provider-specific URL helpers; see [Current Providers](current_providers.md)
- `newsr.providers.topic`: dynamic watched-topic provider that searches the web for a stored topic query and extracts readable article content from search results
- `newsr.providers.llm`: OpenAI-compatible client for article categorization, headline translation, body translation, summaries, "more info" synthesis, search-query generation, and article Q&A answers
- `newsr.providers.search`: DuckDuckGo search adapter used by the "more info" and article Q&A flows
- `newsr.cancellation`: cooperative cancellation primitive (`RefreshCancellation`) and shared `cancellable_read` helper used by all HTTP-fetching providers
- `newsr.export`: Markdown and PNG export services plus clipboard integration
- `newsr.storage`: SQLite connection, schema setup, article persistence, provider/target persistence, permanent duplicate-id tracking, scoped reader state, and single-row global options. The `NewsStorage` facade delegates article methods to `ArticleStore` via `__getattr__` and defines provider, reader-state, options, and lifecycle methods explicitly.
- `newsr.pipeline`: refresh orchestration that runs a scoped provider set, stores source content, classifies article categories, then runs translation and summary jobs
- `newsr.ui`: the Textual app, themes, provider-home table, and modal screens for help, sources, quick navigation, export, article Q&A, watched-topic creation, open-link confirmation, retry/confirm prompts, free-text input, and "more info"
- `newsr.ui.controllers`: controller objects that encapsulate feature-specific state and logic for article Q&A, article categorization, article rendering, navigation, provider home management, watched-topic creation, export, and background refresh, while the main `NewsReaderApp` stays focused on widget composition, thin forwarding methods for bindings/screen callbacks, `refresh_view()`, and lifecycle cleanup

All network-facing providers use `cancellable_read` from `newsr.cancellation` for chunked HTTP reads with cooperative cancellation support.

Provider catalogs are not uniform. See [Current Providers](current_providers.md) for the current built-in provider list, bootstrap defaults, and catalog behavior.

## Current Features

- Provider home groups `[ALL]`, built-in providers, and watched topics, and can sort visible scopes by unread count or name through `ui.provider_sort`.
- The reader supports full and summary views, per-scope saved article position, saved scroll offset, and a quick-navigation list that only includes translated articles.
- Refresh work is scheduled per provider with a global default cron expression and optional per-provider overrides from the source manager.
- Every refresh session performs an LLM responsiveness check before starting article processing.
- Articles are classified into the fixed app category vocabulary: `ADVERTISEMENT`, `SPORT`, `TECHNOLOGIES`, `AI`, `LIFE`, `MEETUP`, `BUSINESS`, `POLITICS`, `WAR`, `SCIENCE`, `HEALTH`, `SECURITY`, and `CULTURE`.
- The reader can rerun category classification for the current article from stored source text.
- `More Info` builds a cached article-specific context panel from DuckDuckGo results plus LLM synthesis.
- Article Q&A keeps a temporary per-modal transcript, combines stored article text with live DuckDuckGo results, and does not persist chat history after the modal closes.
- Watched topics are dynamic providers backed by DuckDuckGo search and generic readable-content extraction; see [Topic Watch](topic_watch.md).
- Export supports saving or copying Markdown and PNG output for the current article view.
- Opening an article URL uses an in-app confirmation screen before handing the link to the browser.
- UI language currently supports `en` and `ru`, and the selected Textual theme is persisted in SQLite options.

## Runtime Flow

1. `newsr.app.main` first patches missing `ui.locale` into existing `newsr.yml` files when needed, then runs interactive first-run bootstrap only when `newsr.yml` does not exist yet.
2. `NewsReaderApp` opens `cache/newsr.sqlite3`, initializes schema, builds the built-in HTTP provider registry, and calls the provider-home bootstrap controller, which syncs built-in provider rows into SQLite and seeds provider targets when a provider has not been initialized yet.
3. Bootstrap enables `bbc` by default and seeds each built-in provider's initial selected targets from `default_targets()`. Watched-topic providers are stored in SQLite as `provider_type = "topic"` rows with a single `watch` target that carries the saved topic query, and `rebuild_provider_registry()` adds them back into the live in-memory registry on startup.
4. Startup prunes expired articles, restores the selected theme from global options, restores the `[ALL]` reader scope, loads cached articles, and opens the provider home as the app's home screen with enabled providers sorted by `ui.provider_sort`; the `[ALL]` row is included there when `ui.show-all` is `true`.
5. The app starts a minute-based scheduler loop. When no refresh or LLM preflight is already running, the scheduler selects enabled providers whose effective cron schedule is due. `[ALL]` is a synthetic `provider_type = "all"` scope and is never selected as a real refresh target.
6. Before each refresh session begins, the refresh controller sends a lightweight responsiveness probe to the configured LLM endpoint. If the probe fails, the UI shows a localized retry dialog and only starts the scoped refresh pipeline after the probe succeeds. The pipeline then walks the selected providers and their selected targets from SQLite, fetches candidates, skips article ids already present in the permanent duplicate table, extracts article bodies, stores source content, classifies each article into zero or more fixed app categories through the configured translation-model endpoint, translates both titles and bodies, generates summaries, and only then marks the article id as permanently known. Each article gets a single `articles.timeout` budget that covers fetch and all LLM stages. When that budget is exceeded, NewsR logs the timeout, deletes the partial article row, records the failed job state, and marks the article id as known. Permanent fetch-validation failures also mark the id as known.
7. The UI refreshes incrementally as translated articles and summaries become available. Status updates and terminal resizes only recompute width-sensitive chrome such as frame titles, URLs, the status line, and the category-enhanced article header; the main article markdown is only replaced when the article content actually changes.
8. Entering `[ALL]` opens the cross-provider article reader, while entering a concrete provider filters the reader to that provider only. The reader and provider-home counters only include articles whose translation is complete. Each scope has its own saved current article, view mode, and scroll offset, and pressing `Esc` from the reader returns to the provider home. Pressing `K` in the reader reruns category classification for the current article from its stored source text and updates the saved article metadata in place.
9. Pressing `W` in provider home opens the watched-topic creation dialog. Pressing `W` in the reader asks the configured LLM to extract a topic name from the current article, then opens the same editable dialog. New watched topics are created as topic providers in SQLite and can immediately force-refresh their own scope when the refresh controller is idle.
10. The source manager can refresh an HTTP provider catalog through `discover_targets()`, persist replacement target lists while preserving still-valid selections, edit per-provider cron overrides, and delete watched-topic providers.
11. Reader state such as the current article, view mode, and scroll offset is persisted per scope, while the selected theme is stored separately in the single-row options table.
12. "More info", article Q&A, open-link confirmation, browser handoff, and export actions run outside the refresh pipeline but reuse the same stored article content, provider registry, DuckDuckGo search client, and configured LLM endpoint. "More info" results are cached per article in SQLite, while article-Q&A transcripts remain modal-local and are discarded when the screen closes.

## Local State

- `newsr.yml`: user config for global refresh, LLM, translation, UI, and export settings; see [Configuration](configuration.md)
- `cache/newsr.sqlite3`: provider registry state, provider types, watched-topic settings, provider schedule overrides, discovered targets, selected targets, article source text, translated text, summaries, cached `more_info`, permanent known article ids, assigned article categories, job state, scoped reader state, and global options
- `cache/newsr-llm.log`: request log for LLM calls plus non-provider network request metadata such as DuckDuckGo search URLs, methods, statuses, and errors
- `exports/`: saved Markdown and PNG exports, created on demand
