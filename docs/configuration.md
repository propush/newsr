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
- Bootstrap writes a `tts` section that selects the Edge TTS engine.

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
  brief_context: 100000
  # api_key: sk-...
  # headers:
  #   OpenAI-Organization: org-...

translation:
  target_language: English

ui:
  locale: en
  clock: no_seconds
  show-all: true
  provider_sort:
    primary: unread
    direction: desc

export:
  image:
    quality: fhd

tts:
  engine: edge
  speed: 1.0
  original_language: en
  # request_retries: 2
  # openai:
  #   url: https://api.openai.com/v1
  #   model: gpt-4o-mini-tts
  #   api_key: sk-...
  #   headers: {}
  #   voices:
  #     default: alloy
  # elevenlabs:
  #   url: https://api.elevenlabs.io/v1
  #   model: eleven_multilingual_v2
  #   api_key: ...
  #   voices:
  #     default: <voice id>
  # edge:
  #   voices:
  #     ru: ru-RU-SvetlanaNeural
  # piper:
  #   models_dir: cache/piper
  #   voices:
  #     ru: ru_RU-irina-medium
  # system:
  #   voices:
  #     ru: Milena
  # silero:
  #   models_dir: cache/silero
  #   voices:
  #     ru: xenia
  #     en: en_0
  #   lexicon:
  #     Etched: +этчед
```

## Field Reference

### `articles`

- `fetch`: how many article candidates each selected target keeps from a provider refresh. Must be a positive integer. Loader default: `5`.
- `store`: retention window in days for cached article rows and maximum publication age for watched-topic articles. On startup, NewsR prunes article rows whose `created_at` is older than this cutoff. During watched-topic refreshes, NewsR filters pages whose parsed publication time is older than this cutoff. Must be a positive integer. Loader default: `10`.
- `timeout`: total per-article processing budget in seconds, covering fetch plus all LLM stages. Must be a positive integer. Loader default: `180`.
- `update_schedule`: default 5-field cron expression used by enabled providers whose own `update_schedule` is blank. Loader default: `0 * * * *`.

### `llm`

- `url`: required base URL for the OpenAI-compatible chat endpoint. Trailing `/` is stripped on load.
- `model_translation`: required model used for title translation, body translation, responsiveness checks, and article categorization.
- `model_summary`: required model used for summaries, brief reviews, watched-topic extraction, search-query generation, `More Info`, and article Q&A.
- `api_key`: optional bearer token.
- `headers`: optional mapping of additional HTTP headers. Keys and values must be non-empty strings.
- `request_retries`: number of retries after the first transient transport failure for LLM requests and DuckDuckGo searches created by the app. HTTP error responses and DuckDuckGo challenge pages are not retried. Must be zero or greater. Loader default: `2`.
- `brief_context`: maximum estimated token budget for each brief-generation LLM request, counting input plus requested output. Must be a positive integer. Loader default: `100000`.

### `translation`

- `target_language`: required natural-language target used for translated titles, translated article bodies, summaries, `More Info`, and article-Q&A answers.

### `ui`

- `locale`: required UI language. Current supported values are `en` and `ru`.
- `clock`: titlebar clock mode. Allowed values are `none` (hidden with no clock refresh work), `seconds` (system-local time refreshed every second), and `no_seconds` (system-local hours and minutes refreshed when the minute changes). Loader default: `no_seconds`.
- `show-all`: controls whether the synthetic `[ALL]` scope appears in provider home. Must be a boolean. Loader default: `true`.
- `provider_sort.primary`: provider-home sort key. Allowed values: `unread`, `name`. Loader default: `unread`.
- `provider_sort.direction`: provider-home sort direction. Allowed values: `asc`, `desc`. Loader default: `desc`.

### `export`

- `image.quality`: PNG export size preset. Allowed values: `hd`, `fhd`.
- Bootstrap-generated configs currently write `fhd`.
- If the field is omitted in an older or manually written config, the loader falls back to `hd`.

### `tts`

Text-to-speech settings for the article playlist. The whole section is optional; every field has a loader default.

- `engine`: speech engine. Allowed values: `openai`, `elevenlabs`, `edge`, `piper`, `system`, `silero`. Loader default: `edge`.
  - `openai`: any OpenAI-compatible `POST {url}/audio/speech` endpoint. This covers OpenAI itself and local servers that expose the same API, such as Kokoro-FastAPI, Speaches, or LocalAI.
  - `elevenlabs`: the ElevenLabs text-to-speech API.
  - `edge`: Microsoft Edge online neural voices through the `edge-tts` package. It needs no API key.
  - `piper`: local Piper neural voices that run inside NewsR on the CPU.
  - `system`: operating-system voices, using `say` on macOS and `espeak-ng` (or `espeak`) on other platforms.
  - `silero`: local Silero voices for Russian and English that run inside NewsR on the CPU. It needs the optional dependencies: `pip install -e ".[silero]"` in the NewsR virtualenv. See [Silero Engine](#silero-engine).
- `speed`: speech speed multiplier from `0.5` to `2.0`. Loader default: `1.0`. ElevenLabs accepts `0.7` to `1.2`, and NewsR clamps the value to that range for it. Silero has five speed steps, and NewsR uses the nearest one: x-slow below `0.77`, slow below `0.92`, normal below `1.1`, fast below `1.35`, and x-fast from `1.35`.
- `original_language`: language code assumed for Latin-script text in `original` reader mode. Loader default: `en`.
- `request_retries`: number of retries after the first transient failure (network errors, HTTP 429 and 5xx) for the `openai` and `elevenlabs` engines. Must be zero or greater. Loader default: `2`.
- `openai.url`: base URL of the OpenAI-compatible API. Trailing `/` is stripped on load. Loader default: `https://api.openai.com/v1`.
- `openai.model`: speech model name. Loader default: `gpt-4o-mini-tts`.
- `openai.api_key`: optional bearer token.
- `openai.headers`: optional mapping of additional HTTP headers. Keys and values must be non-empty strings.
- `elevenlabs.url`: base URL of the ElevenLabs API. Loader default: `https://api.elevenlabs.io/v1`.
- `elevenlabs.model`: ElevenLabs model id. Loader default: `eleven_multilingual_v2`.
- `elevenlabs.api_key`: API key. Required when `engine` is `elevenlabs`.
- `piper.models_dir`: directory for downloaded Piper voices and the Piper voice index. Loader default: `cache/piper`.
- `silero.models_dir`: directory for downloaded Silero models, the RUNorm transliteration model, and the transliteration cache. Loader default: `cache/silero`.
- `silero.lexicon`: optional mapping from a word, name, or acronym to its Russian pronunciation in Cyrillic, with `+` before the stressed vowel (`Etched: +этчед`). Keys and values must be non-empty strings. Keys with Latin letters match English names inside Russian text, ignoring case, and may hold several words (`Jane Street`). Cyrillic keys replace whole Russian words; all-caps keys such as `США` match case-sensitively. Entries take precedence over the built-in pronunciations.
- `<engine>.voices`: optional mapping from a language code (`en`, `ru`, `de`, ...) or `default` to a voice name of that engine. `elevenlabs.voices.default` is required when `engine` is `elevenlabs`.

Each spoken article consists of an intro, the title, and the body. The intro names the provider and the article position, for example `BBC News. Article 4 of 10.` It uses the UI language. The title and body follow the reader mode of the scope the article was queued from:

- `full` and `summary` text is spoken in `translation.target_language`. English and native language names, ISO codes such as `pt` or `pt-BR`, and names such as `Brazilian Portuguese` are recognized. For an unrecognized name, the language is detected from the script of the translated text.
- `original` text is spoken in the language detected from its script. Cyrillic, Greek, Armenian, Georgian, Hebrew, Arabic, Indic, Thai, Lao, Khmer, Burmese, Ethiopic, Chinese, Japanese, and Korean scripts are recognized; Latin-script text uses `original_language`.

Voice selection per language:

- `openai`: `voices.<language>`, then `voices.default`, then `alloy`. OpenAI voices speak every supported language.
- `elevenlabs`: `voices.<language>`, then `voices.default`. The multilingual models speak every supported language with one voice.
- `edge`: `voices.<language>`; otherwise the first voice that Edge lists for the language, preferring the main regional locale such as `en-US` or `ru-RU`. If Edge returns no audio for an automatically chosen voice, NewsR retries with the next voice for that language. `voices.default`, then `en-US-EmmaMultilingualNeural`, covers languages without a voice.
- `piper`: `voices.<language>`; otherwise the first `medium` quality voice for the language from the Piper voice index, preferring the main regional locale. `voices.default`, then `en_US-lessac-medium`, covers languages without a voice. Voice names follow the Piper format `<language>_<REGION>-<name>-<quality>`. NewsR downloads missing voices from the `rhasspy/piper-voices` repository into `models_dir` on first use.
- `system`: `voices.<language>`; otherwise, on macOS, the first installed `say` voice for the language, preferring the main regional locale and skipping novelty voices. On other platforms the language code is passed to `espeak-ng` as the voice.
- `silero`: `voices.ru`, then `xenia`, for Russian; `voices.en`, then `en_0`, for English. Russian voices are `aidar`, `baya`, `eugene`, `kseniya`, and `xenia`; English voices are `en_0` to `en_117`. Text without a language is spoken in Russian when it has more Cyrillic than Latin letters, otherwise in English. Other languages stop playback with an error.

### Silero Engine

Silero voices read letters only: digits, symbols, and, for the Russian voices, Latin letters are skipped. NewsR therefore rewrites every text before the Silero engine speaks it.

Russian text:

- Numbers, years, dates, times, ordinals, units (`млн`, `млрд`, `%`, `ГБ`, `Гбит/с`, `мАч`, and others), and currency amounts are written as Russian words in the grammatical case required by the surrounding words: `до 40%` becomes `до сорока процентов`, `28 сентября 2026 г.` becomes `двадцать восьмого сентября две тысячи двадцать шестого года`.
- English names and brands are written in Cyrillic. NewsR looks them up in `silero.lexicon`, then in a built-in list of frequent tech names with stress marks, then transliterates them with the RUNorm model. Names that RUNorm can only spell letter by letter go to the configured LLM (`llm.model_translation`). Transliterations are cached in `transliterations.json` inside `silero.models_dir`, so each name sounds the same every time; edit or delete entries there to change them.
- Version numbers inside names are read with `точка` (`Beta 6.1` becomes `бета шесть точка один`).
- Latin and Cyrillic acronyms are spelled letter by letter and stressed on the last letter (`TSMC` becomes `ти-эс-эм-си`, `ФРС` becomes `эф-эр-эс`). Acronyms read as words, such as `NASA` and `НАТО`, are kept as words.

English text: numbers, years, currency amounts, percentages, and units are written as English words, and acronyms are spelled with English letter names (`TSMC` becomes `tee-ess-em-see`).

Without the optional dependencies, playback stops with an error that names the install command and the missing packages, and nothing is downloaded. Downloads happen on first use and go to `silero.models_dir`: the Russian model `v5_ru` (145 MB) from `models.silero.ai`, the English model `v3_en` (57 MB) when English text is spoken, and the RUNorm model (17 MB) from Hugging Face when an English name needs transliteration. The optional Python dependencies take about 210 MB to download and about 1 GB on disk on macOS, mostly PyTorch. On Linux, install the CPU-only PyTorch build first (`pip install torch --index-url https://download.pytorch.org/whl/cpu`), because the default Linux build also pulls in GPU libraries.

## Scheduling Notes

- `articles.update_schedule` is the global default schedule.
- Each provider row in SQLite can override that schedule with its own `update_schedule`.
- Watched-topic creation accepts an optional schedule override and leaves it blank to inherit `articles.update_schedule`.
- Schedules use the app's validated 5-field cron format.

## Runtime Files

- `newsr.yml`: global app configuration.
- `cache/newsr.sqlite3`: providers, targets, topic watches, article content, translations, summaries, cached `more_info`, reader state, options, the article playlist, and refresh bookkeeping.
- `cache/newsr-tts.log`: text-to-speech log with engine, voice, request size, retry, download, and error metadata. Spoken text is not logged.
- `cache/piper/`: downloaded Piper voices and the Piper voice index, when `tts.piper.models_dir` keeps its default.
- `cache/silero/`: downloaded Silero models, the RUNorm transliteration model, and `transliterations.json`, when `tts.silero.models_dir` keeps its default.
- `cache/tts/`: temporary files used while the `system` engine synthesizes speech.
- `cache/newsr-llm.log`: LLM request log, transient transport retry metadata, brief-generation stage metadata, repair retry metadata, and non-provider network request metadata. Entries include request method, URL, status, retry attempt, brief stage, validation counts, and errors without logging response contents.
- `exports/`: Markdown and PNG exports created by the export flow.
