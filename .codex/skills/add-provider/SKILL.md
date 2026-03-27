---
name: add-provider
description: Add a new provider integration to the NewsR project. Use when a user wants to add a news source/provider, create a package under `src/newsr/providers/`, wire it into `src/newsr/providers/registry.py`, decide bootstrap defaults, add provider fixtures/tests, or update provider-related docs. Start by requesting the provider URL, then use `$brainstorming` to clarify provider behavior and constraints before implementation.
---

# Add Provider

## Overview

Add a provider the same way the existing built-ins were added: keep provider-specific logic inside the provider package and preserve the generic refresh, storage, and UI paths.

Use `docs/add_provider.md` as the primary implementation guide. Do not duplicate that guide; read it first and follow it closely.

## Workflow

### 1. Build context first

Read these project files before making design claims:

- `docs/add_provider.md`
- `src/newsr/providers/base.py`
- `src/newsr/providers/registry.py`
- one dynamic provider and one static provider package under `src/newsr/providers/`
- `src/newsr/ui/app.py` for bootstrap defaults
- matching provider tests under `tests/providers/`

Identify what already exists and what the new provider must supply without adding special cases.

### 2. Start with `$brainstorming`

Do not jump into implementation. Invoke `$brainstorming` and stay in design mode until the understanding lock is confirmed.

If the provider URL is missing, ask for it first. Use a direct question such as: `What provider URL should this integration target?`

During brainstorming, make sure the discussion explicitly covers:

- `provider_id`
- display name
- target model: `category`, `tag`, `topic`, `feed`, or another generic kind
- whether targets are static, discoverable, or mixed
- stable `provider_article_id` derivation
- candidate link detection and dedupe rules
- title/body/author/published-date extraction
- bootstrap defaults: enabled by default or not, selected targets or not
- performance, reliability, and maintenance assumptions

Ask one question at a time and do not implement anything until the user confirms the understanding summary.

### 3. Implement from the guide

After the design is confirmed, follow `docs/add_provider.md` exactly:

- add a provider package under `src/newsr/providers/<provider_id>/`
- keep parsing and URL normalization in helpers where possible
- register the provider in `src/newsr/providers/registry.py`
- keep provider-specific behavior out of pipeline, storage, and source-manager code unless there is a real new generic requirement
- use `cancellable_read` in every network-facing path
- preserve provider-scoped article ids
- keep new providers disabled by default unless there is a clear reason not to

### 4. Deliver a complete change

The expected deliverable usually includes:

- provider package files under `src/newsr/providers/<provider_id>/`
- fixture-backed tests under `tests/providers/<provider_id>/`
- HTML fixtures under `tests/fixtures/`
- any registry/bootstrap adjustments
- docs updates under `docs/` when the documented workflow or architecture changes

### 5. Validate before finishing

Run the most relevant tests for the provider work you changed, then expand if needed. At minimum, run the provider-specific tests and any impacted registry, pipeline, storage, or UI tests.

Confirm the final state against the guide's manual verification and definition-of-done sections.

## Guardrails

- Do not add provider-specific branches to generic paths unless multiple providers need the abstraction.
- Do not store provider enablement or target selections in `newsr.yml`.
- Do not use weak article identities such as titles or list indexes.
- Do not stop after code changes; include tests and docs updates when required.

## Output

When the work is done, summarize:

- the provider URL and chosen `provider_id`
- the target strategy
- the stable article id strategy
- files changed
- tests run
- any assumptions or follow-up risks
