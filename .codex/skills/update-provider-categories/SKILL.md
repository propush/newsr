---
name: update-provider-categories
description: Audit existing NewsR article providers against live publisher categories and update catalogs, affected parsers, tests, and documentation. Use for category additions, removals, renamed sections, broken category URLs, or a full provider catalog refresh; adding a new provider is a separate workflow.
---

# Update Provider Categories

Reconcile NewsR's built-in target catalogs with current first-party publisher evidence and implement the changes. This is an on-demand snapshot audit. Keep the existing discovery model unless the user requests ongoing discovery.

## Scope and Repository Context

- Default to all built-in providers in `src/newsr/providers/registry.py`; limit the work to named providers when requested. Honor audit-only requests without editing tracked files.
- Use main editorial navigation and primary topic indexes. Preserve the provider-specific boundaries documented in `docs/current_providers.md`; do not expand into exhaustive tags, individual product models, or podcast-only destinations without a request.
- Proceed with the update using these defaults; ask only when a missing decision materially changes the scope or makes a category mapping ambiguous.
- Read `AGENTS.md`, `docs/current_providers.md`, and the affected provider packages and tests. The documentation is the canonical provider list; compare it with `build_provider_registry()` and each provider's `default_targets()` to identify drift. Derive counts from code, not a fixed number in this skill.
- Most static definitions are in `src/newsr/providers/<provider_id>/catalog.py`; BBC uses `categories.py` and also supports live navigation discovery. Read `provider.py`, `urls.py`, and `parsing.py` for each affected provider.

## Verify the Live Catalogs

1. Inspect each publisher's current navigation and documented topic index to discover additions and renamed sections. Check every existing target in scope, including entries absent from the current menu. Follow redirects and inspect the actual destination.
2. Verify that a target represents the intended editorial section. A 200 response can be a soft 404, generic homepage, challenge page, or empty listing. Preserve meaningful URL capitalization and distinguish section hubs from their article-bearing listing endpoints.
3. Run the provider's candidate parser against fetched listing HTML or its actual discovery response. Check native article URLs, target relevance, deduplication, and exclusion of sponsored, video, podcast, and index links according to that provider's contract. Parse a representative written article per provider and for newly introduced layouts, checking title, readable body, author, and date where supplied.
4. Keep compact evidence notes with target key, label, requested and final destinations, HTTP/content status, extracted candidate count, first-party source, and verification date. Store temporary downloads outside tracked files and local runtime data. Retain only minimal sanitized test fixtures in the repository.

Use live first-party pages as the authority. Indexed first-party evidence can establish that a category exists when direct access is blocked, but does not verify the HTTP provider's parser. Record that distinction. Do not remove targets solely because of a 403, timeout, missing menu entry, or one empty response. For unresolved access failures, preserve the target and document the verification limit after reasonable checks. Published empty topic pages can remain in the catalog with an explicit empty-result note; do not substitute unrelated homepage articles.

## Implement the Reconciliation

- Update the provider's catalog labels and destinations. Add confirmed editorial categories. Retire a target only when evidence establishes removal or an unsupported destination with no valid equivalent.
- Preserve stable target keys for the same editorial meaning, even when the publisher changes its label or URL. Do not silently transfer a selection to a different subject. Leave existing bootstrap selections intact unless a retired target or the requested scope requires a change; document any new-installation default changes.
- Fix URL recognition, listing extraction, or article parsing only where live evidence shows the catalog cannot work. Keep logic in the relevant provider package or an existing shared provider helper; retain cooperative cancellation and provider-scoped article identities.
- Check startup synchronization in `src/newsr/ui/controllers/provider_home.py` and transactional replacement in `src/newsr/storage/provider_store.py`. Existing installations must receive updated metadata while preserving enabled states, schedules, retained selections, explicit empty selections, watched topics, and stored articles. New targets stay unselected on existing installations. Preserve BBC's additional stored live-discovered targets during startup synchronization.
- Do not modify generated `newsr.yml`, cache files, or the user's SQLite database to deliver the update. Catalog upgrades belong in code. No new provider integration or configuration option is implied by a catalog refresh.

## Tests, Documentation, and Completion

- Add or update fixture-backed regressions for changed layouts and candidate routing. Cover meaningful migration behavior when synchronization changes, including preserved selections and removal of retired targets. Network-dependent tests should use captured fixtures or fakes.
- Run focused provider tests and affected storage/UI tests, then the full suite with `./venv/bin/pytest` when the repository virtualenv is available. Run `git diff --check` before finishing.
- Update `docs/current_providers.md` with current targets, destinations, defaults, first-party references, audit dates, and access or empty-listing limitations. For a partial audit, date the affected provider notes and retain the full-audit date until all providers have been checked. Keep concrete provider lists in this canonical file and have other docs reference it. Update architecture docs only when behavior changes, and `docs/configuration.md` if configuration settings change. Describe the current state without comparing it to prior behavior.
- Finish with the providers checked, notable additions/corrections/removals, tests run, and remaining verification limits. Distinguish verified parser results from category-existence evidence; do not claim blocked endpoints were fully verified.

## Example Requests

- `$update-provider-categories` — audit and update all built-in providers.
- `$update-provider-categories for BBC and EdSurge` — update only those providers.
- `$update-provider-categories audit only` — report drift and evidence without changing tracked files.
