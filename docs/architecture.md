# Architecture

NewsR is a single-process local terminal application. It runs from the repository root, keeps its state in SQLite under `cache/`, and uses a provider-backed refresh pipeline to keep the Textual UI responsive while content is fetched and processed.

## Package Layout

- `newsr.app`: process bootstrap and CLI entrypoint used by `newsr` and `python -m newsr`
- `newsr.config`: config dataclasses plus loading and validation for `newsr.yml`, including UI locale, `[ALL]` provider-home visibility, and provider-home sort settings
- `newsr.domain`: shared article, provider, and reader-state models used across UI, storage, and pipeline code
- `newsr.ui_text`: built-in UI locale definitions plus localized labels, prompts, hints, and status text used by both bootstrap and the Textual app
- `newsr.providers.base`: `NewsProvider` protocol used by the refresh pipeline
- `newsr.providers.registry`: built-in provider registration; see [Current Providers](current_providers.md) for the current built-in news provider set
- `newsr.providers.<provider_id>`: built-in provider packages for target discovery, section parsing, article extraction, and provider-specific URL helpers; see [Current Providers](current_providers.md)
- `newsr.providers.llm`: OpenAI-compatible client for headline translation, body translation, summaries, "more info" synthesis, search-query generation, and article Q&A answers
- `newsr.providers.search`: DuckDuckGo search adapter used by the "more info" and article Q&A flows
- `newsr.cancellation`: cooperative cancellation primitive (`RefreshCancellation`) and shared `cancellable_read` helper used by all HTTP-fetching providers
- `newsr.export`: Markdown and PNG export services plus clipboard integration
- `newsr.storage`: SQLite connection, schema setup, article persistence, provider/target persistence, scoped reader state, and single-row global options. The `NewsStorage` facade delegates article methods to `ArticleStore` via `__getattr__` and defines provider, reader-state, options, and lifecycle methods explicitly.
- `newsr.pipeline`: refresh orchestration that walks enabled providers and selected targets, stores source content, then runs translation and summary jobs
- `newsr.ui`: the Textual app, themes, controllers, and modal screens for help, sources, quick navigation, export, article Q&A, open-link confirmation, and "more info"
- `newsr.ui.controllers`: controller objects that encapsulate feature-specific state and logic — article Q&A, "more info", article rendering, navigation, provider home management, and background refresh — keeping the main `NewsReaderApp` class thin with forwarding methods

All network-facing providers use `cancellable_read` from `newsr.cancellation` for chunked HTTP reads with cooperative cancellation support.

Provider catalogs are not uniform. See [Current Providers](current_providers.md) for the current built-in provider list, bootstrap defaults, and catalog behavior.

## Runtime Flow

1. `newsr.app.main` first patches missing `ui.locale` into existing `newsr.yml` files when needed, then runs interactive first-run bootstrap only when `newsr.yml` does not exist yet.
2. `NewsReaderApp` opens `cache/newsr.sqlite3`, initializes schema, builds the provider registry, and bootstraps missing provider and target rows into SQLite.
3. Bootstrap syncs provider rows for all built-in providers, enables `bbc` by default, and seeds each provider's initial selected targets from `default_targets()`.
4. Startup prunes expired articles, restores the selected theme from global options, restores the `[ALL]` reader scope, loads cached articles, and opens the provider home as the app's home screen with enabled providers sorted by `ui.provider_sort`; the `[ALL]` row is included there when `ui.show-all` is `true`.
5. The app starts a background refresh on launch. The refresh pipeline walks enabled providers and their selected targets from SQLite, fetches candidates, skips cached articles, extracts article bodies, stores source content, translates both titles and bodies through the configured LLM endpoint, and then generates summaries.
6. The UI refreshes incrementally as translated articles and summaries become available. Status updates and terminal resizes only recompute width-sensitive chrome such as frame titles, URLs, and the status line; the main article markdown is only replaced when the article content actually changes.
7. Entering `[ALL]` opens the cross-provider article reader, while entering a concrete provider filters the reader to that provider only. The reader and provider-home counters only include articles whose translation is complete. Each scope has its own saved current article, view mode, and scroll offset, and pressing `Esc` from the reader returns to the provider home.
8. The source manager can refresh a provider catalog through `discover_targets()`, persist the replacement target list, and preserve still-valid selections.
9. Reader state such as the current article, view mode, and scroll offset is persisted per scope, while the selected theme is stored separately in the single-row options table.
10. "More info", article Q&A, open-link confirmation, browser handoff, and export actions run outside the refresh pipeline but reuse the same stored article content, provider registry, and configured LLM endpoint.

## Local State

- `newsr.yml`: user config for refresh limits, LLM endpoint/model settings, translation language, UI locale (`en` or `ru`), `[ALL]` provider-home visibility (`ui.show-all = true|false`), provider-home sorting (`ui.provider_sort.primary = unread|name`, `ui.provider_sort.direction = asc|desc`), and export quality
- `cache/newsr.sqlite3`: provider registry state, discovered targets, selected targets, article source text, translated text, summaries, job state, scoped reader state, and global options
- `cache/newsr-llm.log`: request log for LLM calls
- `exports/`: saved Markdown and PNG exports, created on demand
