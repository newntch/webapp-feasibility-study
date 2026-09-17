# Repository Guidelines
## Prime Directive

- DO NOT stop until the tasks are completed.
- DO NOT introduce anti-patterns or quick hacks at all costs. Avoid technical debt.
- When coding, do test-driven development by spawning a subagent to write the tests, so that the test is blinded to the code prior to the run.
- Put temp files in the `temp` directory. Do not delete `temp` directory.
- If presented with irreversible options, ask first, don't anticipate my needs.
- I use `pnpm` (not `npm`) for JavaScript package management.
- I use `uv` for Python environment management.
- prefer each script file to have less 1000 lines. If longer than that, plan modularization.

Deliver results that are:

1. **Correct** (matches the request and repo conventions)
2. **Safe** (no destructive actions without explicit authorization)
3. **Verifiable** (commands run, evidence shown, uncertainty stated)
4. **Minimal** (small diffs, little churn, no needless dependencies)

## Project Structure & Module Organization
Keep all project files inside `webapp-feasibility-study/`; do not add or modify files in the parent repository unless explicitly requested.

Use a predictable layout:
- `src/apps/` and `src/config/` for Django code
- `src/core/` for plain browser modules served by Django
- `tests/django/` for automated tests
- `public/` for static browser files
- `docs/` for design notes and operational guidance

Favor small, focused modules and keep related tests near the feature they validate or under `tests/` with matching names.

## Build, Test, and Development Commands
This project uses Django and two PostgreSQL databases. No Node runtime or JavaScript package manager is required.

- `docker compose up -d` starts the local database and web service at `http://localhost:4173`.
- `uv run pytest -q` runs the Python and Django tests.
- `uv run ruff check src tests/django` checks Python style.
- `uv run python manage.py sync_dictionary` refreshes the public dictionary snapshot.

Scope Git commands to this folder because the Git root is the parent directory:
- `git status -- webapp-feasibility-study`
- `git diff -- webapp-feasibility-study`
- `git add webapp-feasibility-study/`

Keep browser JavaScript as plain modules unless a future change explicitly requires a build step.

## Coding Style & Naming Conventions
Use 2 spaces for indentation in Markdown, JSON, YAML, and frontend code unless the selected stack has a stronger convention. Name files by purpose:
- `kebab-case` for filenames: `market-sizing-notes.md`
- `PascalCase` for React components: `StudyDashboard.tsx`
- `camelCase` for functions and variables

Adopt a formatter and linter with the first real code contribution and commit their config with the code that depends on it.

## Testing Guidelines
The current tests use pytest and Django's test client. Require tests for core logic and any calculations, parsers, or scoring rules used in the feasibility study.

Prefer names that mirror behavior, such as `tests/django/test_clinical_sql.py`.

## Commit & Pull Request Guidelines
The visible history only contains `first commit`, so there is no reliable existing convention to preserve. Use short, imperative commit subjects instead:
- `Add initial feasibility study structure`
- `Create cost model test scaffold`

Pull requests should stay narrowly scoped, summarize the change, list validation performed, and include screenshots when UI work is introduced.

## Agent-Specific Notes
Because this folder lives inside a larger Git repository, contributors and agents should avoid repo-wide commands unless they intentionally target the parent project. Keep searches, diffs, and staging limited to `webapp-feasibility-study/`.
