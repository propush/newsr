# Configuration

This page documents the current `newsr.yml` schema and the local files NewsR maintains at runtime.

Provider enablement, target selection, watched-topic definitions, and per-provider schedule overrides are not stored in `newsr.yml`. They live in SQLite and are managed through the source manager. For the concrete built-in provider list and bootstrap defaults, see [Current Providers](current_providers.md).

## Bootstrap Behavior

- NewsR runs from the repository root and expects `newsr.yml` there.
- On first run, interactive bootstrap creates `newsr.yml`.
- For an existing config that is missing `ui.locale`, NewsR patches that field interactively before loading the rest of the config.
- Bootstrap currently offers a local or cloud LLM backend.
- The generated local default is `http://localhost:8081/v1` with model `local-translate`.
- The generated cloud default is `https://api.openai.com/v1` with model `gpt-4.1-mini`.
- Bootstrap suggests both UI language and translation language from the current system locale.

## Current Schema

```yaml
articles:
  fetch: 5
  store: 10
  timeout: 180
  update_schedule: "0 * * * *"

llm:
  url: http://localhost:8081/v1
  model_translation: local-translate
  model_summary: local-translate
  request_retries: 2
  # api_key: sk-...
  # headers:
  #   OpenAI-Organization: org-...

translation:
  target_language: English

ui:
  locale: en
  show-all: true
  provider_sort:
    primary: unread
    direction: desc

export:
  image:
    quality: fhd
```

## Field Reference

### `articles`

- `fetch`: how many article candidates each selected target keeps from a provider refresh. Must be a positive integer. Loader default: `5`.
- `store`: retention window in days for cached article rows. On startup, NewsR prunes articles whose `created_at` is older than this cutoff. Must be a positive integer. Loader default: `10`.
- `timeout`: total per-article processing budget in seconds, covering fetch plus all LLM stages. Must be a positive integer. Loader default: `180`.
- `update_schedule`: default 5-field cron expression used by enabled providers whose own `update_schedule` is blank. Loader default: `0 * * * *`.

### `llm`

- `url`: required base URL for the OpenAI-compatible chat endpoint. Trailing `/` is stripped on load.
- `model_translation`: required model used for title translation, body translation, responsiveness checks, and article categorization.
- `model_summary`: required model used for summaries, watched-topic extraction, search-query generation, `More Info`, and article Q&A.
- `api_key`: optional bearer token.
- `headers`: optional mapping of additional HTTP headers. Keys and values must be non-empty strings.
- `request_retries`: number of retries after the first failed request. Must be zero or greater. Loader default: `2`.

### `translation`

- `target_language`: required natural-language target used for translated titles, translated article bodies, summaries, `More Info`, and article-Q&A answers.

### `ui`

- `locale`: required UI language. Current supported values are `en` and `ru`.
- `show-all`: controls whether the synthetic `[ALL]` scope appears in provider home. Must be a boolean. Loader default: `true`.
- `provider_sort.primary`: provider-home sort key. Allowed values: `unread`, `name`. Loader default: `unread`.
- `provider_sort.direction`: provider-home sort direction. Allowed values: `asc`, `desc`. Loader default: `desc`.

### `export`

- `image.quality`: PNG export size preset. Allowed values: `hd`, `fhd`.
- Bootstrap-generated configs currently write `fhd`.
- If the field is omitted in an older or manually written config, the loader falls back to `hd`.

## Scheduling Notes

- `articles.update_schedule` is the global default schedule.
- Each provider row in SQLite can override that schedule with its own `update_schedule`.
- Watched-topic creation accepts an optional schedule override and leaves it blank to inherit `articles.update_schedule`.
- Schedules use the app's validated 5-field cron format.

## Runtime Files

- `newsr.yml`: global app configuration.
- `cache/newsr.sqlite3`: providers, targets, topic watches, article content, translations, summaries, cached `more_info`, reader state, options, and refresh bookkeeping.
- `cache/newsr-llm.log`: LLM request log plus non-provider network request metadata. Entries include request method, URL, status, and errors without logging response contents.
- `exports/`: Markdown and PNG exports created by the export flow.
