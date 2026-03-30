# NewsR

NewsR is a local-first terminal news reader with a provider-backed source model. It ships with multiple built-in news providers, translates full articles through an OpenAI-compatible LLM endpoint, stores local state in SQLite, and generates summaries for fast reading in a Textual UI. See [Current Providers](docs/current_providers.md) for the current built-in provider list and bootstrap defaults.

NewsR currently requires Python 3.12 or newer.

## Features

- built-in support for multiple news providers; see [Current Providers](docs/current_providers.md)
- background refresh with cached startup content
- translated full articles plus summaries
- "more info" and article Q&A overlays backed by DuckDuckGo search and the configured LLM
- source management for enabling providers, refreshing catalogs, and choosing targets
- export of the current view as Markdown or PNG
- PNG and Markdown clipboard export support on supported platforms

## Screenshots

### Reading Views

Full article view:

![Full article view](docs/images/article_full.png)

Summary view:

![Summary view](docs/images/article_summary.png)

Theme switch example:

![Theme change](docs/images/theme_changed.png)

### Navigation And Source Management

Manage sources:

![Manage sources](docs/images/news_sources.png)

Quick navigation:

![Quick navigation](docs/images/quick_navigation.png)

### Contextual Overlays

"More info" overlay:

![More info overlay](docs/images/more_info.png)

Article Q&A overlay:

![Article Q&A overlay](docs/images/article_qa.png)

## Setup

The simplest way to start NewsR from the repository root is:

```bash
./newsr.sh
```

`newsr.sh` uses the Python interpreter already available on your `PATH` (`python3` first, then `python`). If that interpreter is Python 3.12 or newer, the script creates `./venv` when needed, installs NewsR there, and launches the app.

If no compatible Python is available on `PATH`, the script exits with an error instead of trying to install or discover another interpreter.

For development work, you can still create and manage the virtualenv manually:

```bash
python3 -m venv venv
source ./venv/bin/activate
pip install -e ".[dev]"
```

## Start The App

Run NewsR from the repository root so it can find `newsr.yml` and write runtime data under `cache/`.

```bash
./newsr.sh
```

You can also start it with:

```bash
newsr
```

or:

```bash
python -m newsr
```

On first launch, if `newsr.yml` is missing, NewsR starts a terminal setup flow before opening the Textual UI. The setup asks for:

- UI language, with a locale-based default from the built-in supported locales (`English` and `Русский`)
- `local` or `cloud` LLM backend
- an editable default URL for the chosen backend
- a suggested model name
- translation language, with a locale-based suggestion and an `English` fallback
- for cloud mode only: optional API key and optional extra headers

If `newsr.yml` already exists but is missing `ui.locale`, NewsR asks for the UI language before loading the rest of the config and saves the choice back into `newsr.yml`.

After writing `newsr.yml`, NewsR tells you that more settings can be tuned by editing the config file, then waits for Enter before launching the app.

To reconfigure the app from scratch, delete `newsr.yml` and start NewsR again. That reruns the terminal setup flow and writes a fresh config file.

The first launch also creates:

- `newsr.yml`: local config
- `cache/newsr.sqlite3`: source state, cached articles, summaries, and reader state
- `cache/newsr-llm.log`: LLM request log

The `exports/` directory is created on demand when you save a Markdown or PNG export.

## Configuration

The generated `newsr.yml` contains five sections:

- `articles`: how many article candidates to fetch per selected target and how many days of articles to keep in SQLite
- `llm`: the OpenAI-compatible base URL, optional auth settings, optional extra headers, plus a translation model for titles and article bodies and a summary model reused for summaries, "more info", search-query generation, and article Q&A
- `translation`: the target language used for translated headlines, article text, summaries, "more info", and article Q&A answers
- `ui`: the Textual UI locale used for built-in chrome such as hints, modal titles, and status text; current built-in locales are `en` and `ru`
- `export`: image export settings

Example generated config for a local setup:

```yaml
articles:
  fetch: 5
  store: 10
llm:
  url: http://localhost:8081/v1
  model_translation: local-translate
  model_summary: local-translate
  request_retries: 2
translation:
  target_language: English
ui:
  locale: en
export:
  image:
    quality: fhd
```

`export.image.quality` accepts `hd` or `fhd`.
`llm.api_key` is optional for local unauthenticated servers. `llm.headers` can be used for extra OpenAI-compatible provider headers, and `llm.request_retries` controls how many times NewsR retries transient transport failures before surfacing an error.

Example cloud-specific additions:

```yaml
llm:
  url: https://api.openai.com/v1
  model_translation: gpt-4.1-mini
  model_summary: gpt-4.1-mini
  request_retries: 2
  api_key: sk-...
  headers:
    OpenAI-Organization: org-...
```

If you launch NewsR without an interactive terminal and `newsr.yml` is missing, startup fails with a message telling you to create the config file manually.

Source selection is managed in `cache/newsr.sqlite3`. Providers, discovered targets, and the current enabled and selected source state live there and are managed from the TUI.

## Sources

Press `C` to open **Manage Sources**.

- The left pane lists registered providers and whether each one is enabled.
- The right pane lists targets for the currently highlighted provider.
- `Tab` switches panes.
- `Space` toggles the highlighted provider or target.
- `R` refreshes the highlighted provider's target catalog by calling its discovery flow.
- `A` saves the current source configuration.
- `Esc` closes the overlay without applying changes.

For the current built-in provider list, bootstrap defaults, and catalog behavior, see [Current Providers](docs/current_providers.md).

Saving source changes starts a refresh immediately when no refresh is already running. If a refresh is in progress, the new source configuration is saved and picked up by the next refresh cycle.

## Reader Controls

- `Left` / `Right`: previous or next article
- `Up` / `Down`: scroll by a few lines
- `PgUp` / `PgDn` / `B`: page scroll
- `Space`: page down, then move to the next article when already at the end
- `S`: toggle between full article and summary when a summary exists
- `M`: open or refresh the "more info" panel for the current article
- `?`: ask a follow-up question about the current article
- `L`: open the article list
- `C`: open source management
- `E`: open export actions for the current view
- `O`: open the current article in the system browser
- `D`: fetch new articles now
- `Ctrl+P`: open the command palette and switch themes
- `H`: show the in-app help screen
- `Q`: quit

## Overlays

- `M` opens a "more info" overlay that uses DuckDuckGo search results plus the configured LLM to add context beyond the current article.
- `?` opens an article Q&A overlay where you can ask follow-up questions. NewsR also shows related public source links that you can open from the overlay.
- `L` opens quick navigation across translated articles.
- `C` opens the source manager for enabling providers and selecting targets.
- `E` opens the export screen, where you can use the buttons or `1` / `2` / `3` / `4` shortcuts for export actions.

## Export

Press `E` to export the current view. NewsR can:

- save PNG to `exports/`
- copy PNG to the system clipboard
- save Markdown to `exports/`
- copy Markdown to the system clipboard

Exports use the current article view, so summary mode exports the summary and full mode exports the full article body currently shown, preferring translated text when available. PNG exports also use the current Textual theme colors.
Saved export filenames include the local date, a slug derived from `article_id`, and the active mode (`full` or `summary`).

Clipboard export support depends on the platform:

- macOS: built in
- Windows: built in
- Linux: requires `wl-copy` or `xclip`

## Refresh Behavior

- Startup loads cached articles first, then immediately starts a background refresh.
- Refresh iterates enabled providers and their selected targets from SQLite-backed source state.
- Refresh work runs in the background and updates the UI as translations and summaries finish.
- Already cached articles are skipped before fetch and LLM work.
- Near the end of the article list, the app arms another fetch automatically so reading forward can pull in more content.
- Changing sources starts a new refresh immediately when no refresh is already running.

## Additional Documentation

- [Architecture](docs/architecture.md)
- [Adding A Provider](docs/add_provider.md)

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
