# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `src/newsr/` and is split by responsibility. `app/` contains the CLI entrypoint, `config/` owns `newsr.yml` loading and validation, `domain/` holds shared models, `providers/` contains built-in news providers plus search and LLM integrations, `storage/` owns SQLite persistence, `pipeline/` orchestrates background refresh work, and `ui/` contains the Textual app, themes, and modal screens. `cancellation.py` at the package root provides cooperative cancellation and `cancellable_read`, a shared HTTP read helper used by all HTTP-fetching providers. The `NewsStorage` facade in `storage/facade.py` delegates article methods to `ArticleStore` via `__getattr__` and only defines reader-state and lifecycle methods explicitly. Tests mirror that structure under `tests/`, with HTML fixtures under `tests/fixtures/`. Reference docs live in `docs/`, and [docs/current_providers.md](/Users/pushkin/projects/newsr/docs/current_providers.md) is the canonical built-in provider list. Local runtime data is created under `cache/`; do not commit cache files, generated config, or other local state.

## Build, Test, and Development Commands
Create or activate a virtualenv, then install editable dependencies:

```bash
source ./venv/bin/activate
pip install -e ".[dev]"
```

Run the app with `newsr` or `python -m newsr`. Execute the full test suite with `pytest`. During focused work, run a single file such as `pytest tests/ui/test_app.py` or `pytest tests/pipeline/test_refresh.py -k refresh`.

## Coding Style & Naming Conventions
Follow the existing Python style: 4-space indentation, type hints on public functions, and `from __future__ import annotations` in modules. Use `snake_case` for functions, variables, and test names; use `PascalCase` for dataclasses, enums, and other types. Keep modules small and boundary-focused rather than mixing UI, storage, and network logic. No formatter or linter is configured yet, so match the surrounding code closely and keep imports and docstrings minimal.

## Testing Guidelines
Tests use `pytest` with `src` on the Python path. Add tests beside the affected area using the existing package layout such as `tests/config/`, `tests/providers/`, `tests/storage/`, `tests/pipeline/`, and `tests/ui/`, and prefer fixtures in `tests/conftest.py` for reusable app state. Cover storage changes with SQLite-backed tests, pipeline changes with fake provider and LLM objects, provider changes with fixture-backed parsing tests, and UI changes with Textual's `run_test()` flow. New features should include at least one regression test.

## Configuration & Local Data
Run `newsr` from the repository root. On first run it creates `newsr.yml` in the repo root, `cache/newsr.sqlite3` for local data, and `cache/newsr-llm.log` for LLM request logging. Keep secrets or local model endpoints in `newsr.yml` only; never hardcode them in source or fixtures.

## Agent rules
After implementing a feature, always update the tests, check that they run.
Always keep the project documentation consistent in the docs dir.
Treat [docs/current_providers.md](/Users/pushkin/projects/newsr/docs/current_providers.md) as the single source of truth for the implemented built-in provider list and documented bootstrap defaults. When built-in providers change, update that file and have other docs reference it instead of repeating the concrete provider list, except `providers_todo.md`.
