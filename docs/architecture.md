# Architecture

NewsR is a single-process local terminal application. It runs from the repository root, keeps its state in SQLite under `cache/`, and uses a provider-backed refresh pipeline to keep the Textual UI responsive while content is fetched and processed.

## Package Layout

- `newsr.app`: process bootstrap and CLI entrypoint used by `newsr` and `python -m newsr`
- `newsr.config`: config dataclasses plus loading and validation for `newsr.yml`
- `newsr.domain`: shared article, provider, and reader-state models used across UI, storage, and pipeline code
- `newsr.providers.base`: `NewsProvider` protocol used by the refresh pipeline
- `newsr.providers.registry`: built-in provider registration; the current registry ships with BBC News, TechCrunch, The Hacker News, and Ars Technica
- `newsr.providers.bbc`: BBC target discovery, section parsing, article extraction, and URL helpers
- `newsr.providers.techcrunch`: TechCrunch topic catalog, section parsing, article extraction, and URL helpers
- `newsr.providers.thehackernews`: The Hacker News section catalog, section parsing, article extraction, and URL helpers
- `newsr.providers.arstechnica`: Ars Technica mixed feed/section catalog, section parsing, article extraction, and URL helpers
- `newsr.providers.llm`: OpenAI-compatible client for headline translation, body translation, summaries, "more info" synthesis, search-query generation, and article Q&A answers
- `newsr.providers.search`: DuckDuckGo search adapter used by the "more info" and article Q&A flows
- `newsr.cancellation`: cooperative cancellation primitive (`RefreshCancellation`) and shared `cancellable_read` helper used by all HTTP-fetching providers
- `newsr.export`: Markdown and PNG export services plus clipboard integration
- `newsr.storage`: SQLite connection, schema setup, article persistence, provider/target persistence, and saved reader state. The `NewsStorage` facade delegates article methods to `ArticleStore` via `__getattr__` and defines provider, reader-state, and lifecycle methods explicitly.
- `newsr.pipeline`: refresh orchestration that walks enabled providers and selected targets, stores source content, then runs translation and summary jobs
- `newsr.ui`: the Textual app, themes, and modal screens for help, sources, quick navigation, export, article Q&A, open-link confirmation, and "more info"

All network-facing providers use `cancellable_read` from `newsr.cancellation` for chunked HTTP reads with cooperative cancellation support.

Provider catalogs are not uniform:

- `BBC News` supports live target discovery and merges discovered categories with its built-in defaults.
- `TechCrunch` currently exposes a static built-in topic catalog.
- `The Hacker News` currently exposes a static built-in section catalog.
- `Ars Technica` currently exposes a static built-in mixed catalog with a catch-all `latest` feed plus section targets.

## Runtime Flow

1. `newsr.app.main` ensures `newsr.yml` exists in the current working directory, running an interactive terminal bootstrap when it is missing.
2. `NewsReaderApp` opens `cache/newsr.sqlite3`, initializes schema, builds the provider registry, and bootstraps missing provider and target rows into SQLite.
3. Bootstrap syncs provider rows for all built-in providers, enables `bbc` by default, and seeds each provider's initial selected targets from `default_targets()`.
4. Startup prunes expired articles, restores saved reader state, loads cached articles, and shows them immediately when available.
5. The app starts a background refresh on launch. The refresh pipeline walks enabled providers and their selected targets from SQLite, fetches candidates, skips cached articles, extracts article bodies, stores source content, translates them through the configured LLM endpoint, and then generates summaries.
6. The UI refreshes incrementally as translated articles and summaries become available.
7. The source manager can refresh a provider catalog through `discover_targets()`, persist the replacement target list, and preserve still-valid selections.
8. Reader state such as the current article, view mode, scroll offset, and selected theme is persisted back to SQLite.
9. "More info", article Q&A, and export actions run outside the refresh pipeline but reuse the same stored article content and configured LLM endpoint.

## Local State

- `newsr.yml`: user config for refresh limits, LLM endpoint/model settings, translation language, and export quality
- `cache/newsr.sqlite3`: provider registry state, discovered targets, selected targets, article source text, translated text, summaries, job state, and saved reader state
- `cache/newsr-llm.log`: request log for LLM calls
- `exports/`: saved Markdown and PNG exports
