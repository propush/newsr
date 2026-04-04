# Topic Watch

Topic watch lets NewsR track an arbitrary topic as a virtual provider.

## Creating A Watched Topic

- In provider home, press `W` to enter a topic name manually.
- In the reader, press `W` to ask the configured LLM for a topic name derived from the current article, then edit or confirm the suggested value in the same dialog.
- The creation dialog accepts an optional 5-field cron schedule. The dialog shows the configured `articles.update_schedule` value from `newsr.yml`, and leaving the field blank uses it.
- If the saved watched-topic query already exists, NewsR does not create another provider and shows the status `topic already exists: {topic name}`. Duplicate detection normalizes whitespace and compares queries case-insensitively.
- New watched topics are created enabled by default.
- After creation, NewsR starts an immediate force-refresh for that watched topic when the refresh controller is idle. If a refresh is already busy, the app keeps the new topic saved and requests a due-refresh check.

Each watched topic is stored as its own provider row with `provider_type = "topic"` and a single `watch` target carrying the saved topic query.
Watched-topic providers appear in provider home alongside enabled HTTP providers, and the source manager can edit their per-provider schedule or delete them.

## Refresh Model

- Every enabled provider has a nullable `update_schedule`.
- When `update_schedule` is blank, NewsR uses `articles.update_schedule`.
- The app runs a scheduler check once per minute and starts one refresh only when no preflight or refresh is already active.
- `[ALL]` is never refreshed directly.
- Pressing `D` in provider home or while reading `[ALL]` force-refreshes all enabled real providers.
- Pressing `D` while reading a concrete provider force-refreshes only that provider.

## Topic Fetching

Watched topics are fetched through the topic provider:

1. Run a DuckDuckGo web search using the saved topic query.
2. Turn normalized result URLs into stable article ids of the form `web:<normalized_url>`.
3. Download the linked page and extract readable article text.
4. Skip any article id that already exists in the permanent duplicate-id table.
5. Process new articles through the standard categorization, translation, and summary pipeline.

The topic provider stores its own `provider_id` as the watched-topic scope, but article identity is URL-based. The same normalized web URL is treated as the same article even when it appears in multiple watched topics.

## Duplicate Tracking

NewsR keeps a permanent `known_article_ids` table in SQLite. Existing `articles.article_id` values are backfilled into that table during schema initialization. During refresh, an article id is registered only after the article completes the full processing pipeline or when refresh reaches a permanent fetch failure. Duplicate checks use `known_article_ids` as the source of truth even after old article rows are pruned from `articles`.
