# Adding a Provider

NewsR already has a generic provider-backed source model. This guide explains how to add another provider without introducing provider-specific behavior into the pipeline, storage layer, or source manager UI.

Repo-local automation for this workflow lives in `.codex/skills/add-provider/SKILL.md`. That skill starts by requesting the provider URL and routes the clarification phase through `$brainstorming` before implementation.

The current registry already ships with multiple built-in providers. See [Current Providers](current_providers.md) for the canonical built-in provider list and documented bootstrap defaults.

That means the surrounding architecture is already multi-provider, and new provider work should fit into the existing generic paths rather than adding special cases.

## Current Architecture

- `src/newsr/providers/base.py` defines the `NewsProvider` protocol.
- `src/newsr/providers/registry.py` wires built-in providers into `build_provider_registry()`.
- `src/newsr/domain/providers.py` defines `ProviderRecord` and `ProviderTarget`.
- `src/newsr/storage/provider_store.py` persists providers, target catalogs, and selected targets in SQLite.
- `src/newsr/pipeline/refresh.py` iterates enabled providers and selected targets generically.
- `src/newsr/ui/app.py` bootstraps provider state and exposes source-management hooks to the UI.
- `src/newsr/ui/screens/categories.py` implements the generic source manager.

Current built-ins show the intended range of provider behavior. See [Current Providers](current_providers.md) for the current built-in provider set and catalog behavior.

Provider state lives in these SQLite tables:

- `providers`
- `provider_targets`
- `provider_target_selections`

Article identity is provider-scoped:

- `provider_id`
- `provider_article_id`
- `article_id = f"{provider_id}:{provider_article_id}"`

## Design Constraints

- Keep provider-specific behavior inside the provider package.
- Do not add provider-specific branches to the refresh pipeline, storage layer, or source manager unless the new provider introduces a real generic requirement.
- Keep `newsr.yml` for global settings only. Provider enablement and target selection belong in SQLite-backed source state.
- Use `cancellable_read` for HTTP reads so refresh cancellation keeps working.
- Preserve provider-scoped article ids. Do not fall back to titles, list positions, or transient URLs.
- A failure in one provider or one target must not block the rest of the refresh.

## Provider Contract

Implement a class that satisfies `NewsProvider`:

- `provider_id: str`
- `display_name: str`
- `default_targets() -> list[ProviderTarget]`
- `discover_targets(cancellation=None) -> list[ProviderTarget]`
- `fetch_candidates(target, limit, cancellation=None) -> list[SectionCandidate]`
- `fetch_article(candidate, cancellation=None) -> ArticleContent`

Expected semantics:

- `default_targets()` returns the initial target catalog used during bootstrap.
- `discover_targets()` returns the full replacement catalog for that provider. It may perform live discovery or return a static built-in catalog.
- `fetch_candidates()` returns provider-scoped candidate ids and only candidates relevant to the supplied target.
- `fetch_article()` returns the full article content and preserves provider identity.

## Delivery Workflow

### 1. Profile the source

Before writing code, decide:

- `provider_id`
- display name
- target kinds such as `category`, `tag`, `topic`, or `feed`
- whether targets are static, discoverable, or mixed
- how to detect article links reliably
- how to derive a stable `provider_article_id`
- how title, body, author, and published date are extracted

### 2. Create a provider package

Add a package under `src/newsr/providers/<provider_id>/`.

Recommended layout:

- `__init__.py`
- `provider.py`
- `parsing.py`
- `urls.py`
- optional `catalog.py` for built-in targets

Keep parsing and URL normalization as pure helpers outside the provider class where possible so fixture-backed tests stay simple.

### 3. Model targets carefully

Use `ProviderTarget` fields like this:

- `provider_id`: stable provider key
- `target_key`: stable storage key for selection and dedupe
- `target_kind`: generic label such as `category`, `tag`, or `feed`
- `label`: human-readable UI label
- `payload`: provider-local metadata needed to fetch candidates
- `selected`: whether the target should be selected by default after bootstrap or after discovery fallback

Keep provider-local metadata in `payload`. Do not add new generic columns unless multiple providers need the same concept.

### 4. Follow identity rules

For every candidate and article:

- `provider_id` identifies the provider
- `provider_article_id` is stable within that provider
- `article_id` is always `f"{provider_id}:{provider_article_id}"`

Avoid weak identifiers such as:

- transient query-string URLs
- titles
- timestamps alone
- list indexes

If the source has no explicit article id, derive `provider_article_id` from a canonical normalized path.

### 5. Implement the provider

Implementation rules:

- `default_targets()` should return a useful initial catalog, with `selected=True` only for sane defaults.
- `discover_targets()` should return a complete replacement catalog. If the source has no discovery endpoint, returning the static built-in catalog is acceptable.
- `fetch_candidates()` should fetch one target, extract article links, normalize them, dedupe them, and return at most `limit` candidates in page order.
- `fetch_article()` should fetch the article page and extract readable source text without related-link or promo boilerplate.

Use `cancellable_read` in every network-facing path.

### 6. Register the provider

Update `src/newsr/providers/registry.py` so `build_provider_registry()` returns the new provider alongside existing ones.

The registry is the only place where built-in providers should be wired together.

### 7. Decide bootstrap defaults

Startup bootstrapping happens in `NewsReaderApp._bootstrap_provider_state()` in `src/newsr/ui/app.py`.

For each new provider decide:

- should it be enabled by default?
- which targets should be selected by default?

Recommended default:

- keep new providers disabled by default unless they are ready for everyday use

Reason:

- enabling a new provider immediately increases refresh volume and LLM work

Current baseline: see [Current Providers](current_providers.md).

### 8. Add tests

Add tests that match the current project layout:

- fixture-backed parsing tests in `tests/providers/<provider_id>/`
- HTML fixtures in `tests/fixtures/`
- registry coverage if registration logic changes
- pipeline tests if multi-provider behavior changes
- storage tests only if the provider introduces a new edge case around target replacement or selection preservation
- UI tests only if source-manager behavior changes

## Suggested File Changes

For a typical provider, expect these touch points.

### New files

- `src/newsr/providers/<provider_id>/__init__.py`
- `src/newsr/providers/<provider_id>/provider.py`
- `src/newsr/providers/<provider_id>/parsing.py`
- `src/newsr/providers/<provider_id>/urls.py`
- optional `src/newsr/providers/<provider_id>/catalog.py`
- `tests/providers/<provider_id>/test_provider.py`
- `tests/fixtures/<provider_id>_*.html`

### Existing files likely to change

- `src/newsr/providers/registry.py`
- possibly `src/newsr/ui/app.py` if bootstrap defaults need adjustment
- possibly `docs/architecture.md` if the new provider changes the documented system shape

## Parsing Checklist

Use this checklist when implementing any provider parser:

- normalize relative URLs to absolute canonical URLs
- reject obvious non-article links
- dedupe repeated links within a listing page
- derive a stable article id from canonical URL structure when possible
- preserve provider-local target context on each candidate
- make body extraction resilient to small markup changes
- keep paragraph joins readable for later translation and summarization

## Manual Verification Plan

After implementation:

1. Start the app with a clean cache.
2. Confirm the new provider is bootstrapped into `providers`.
3. Confirm targets appear in the source manager.
4. Enable the provider and select at least one target.
5. Run a refresh.
6. Confirm stored articles have provider-scoped `article_id`, correct `provider_id`, and correct `provider_article_id`.
7. Confirm the UI can read and open those articles normally.
8. Confirm disabling the provider removes it from future refresh work without deleting previously fetched articles.
9. Confirm refreshing the catalog preserves selections when `target_key` values remain stable.

## Definition of Done

A provider is complete when all of the following are true:

- it is registered in `build_provider_registry()`
- it implements the `NewsProvider` contract cleanly
- it has stable default targets
- target discovery is either implemented or intentionally omitted
- fetched candidates and articles use provider-scoped ids
- parsing is covered by fixture-backed tests
- the provider appears in the source manager without provider-specific UI code
- refresh succeeds without breaking existing providers
- the relevant test suite passes
