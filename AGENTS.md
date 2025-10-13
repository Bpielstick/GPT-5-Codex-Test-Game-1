# AGENTS.md — How Codex should work in this repo

## Mission
Implement the TDD in /docs/LongFormNovelGenerationTDD.md. Produce a near-publishable novel + KU-ready bundle.

## Rules of engagement
- Always open PRs; never push to main.
- Always run `make qa` before requesting review.
- Keep secrets out of code; use env vars.
- Write/modify tests with every change.
- Prefer small PRs that pass CI to large ones.

## Definitions of done (DoD)
- Unit tests added/updated (≥80% on services).
- Lint (ruff) + type checks (mypy) pass.
- For pipeline changes: include a runnable example and a short report artifact in /artifacts.

## Prohibited
- Committing generated keys, large binaries, or private corpora.
- Disabling gates without test coverage and justification.
