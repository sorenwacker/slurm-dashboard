# Contributing

Development happens on GitLab at https://gitlab.ewi.tudelft.nl/reit/slurm-usage-history, with a mirror on GitHub at https://github.com/sorenwacker/slurm-usage-history. Issues and pull requests on GitHub are read; merges land on GitLab and are mirrored back.

## Setup and gates

The development setup, the test commands, and the quality gates (ruff, vulture, mypy, pytest, vitest, eslint) are documented in [docs/development/local-development.md](docs/development/local-development.md). Install the pre-commit hooks once per clone with `uv run pre-commit install`; they run the same gates as CI.

## Workflow

1. Documentation first: describe the intended behavior under `docs/` before changing code, and keep it current.
2. Write or update a test that fails against the current code, then make it pass.
3. Every rule gets an enforcement mechanism: a failing test, a lint rule, or a CI job. A rule that exists only in prose is not accepted.
4. One issue per branch. Open a merge request as soon as the branch is pushed, draft if unfinished.
5. Commit messages are one line, say why rather than what, and contain no emojis.

## Releases

Releases are tagged on `main` (`vX.Y.Z`) after the changelog section for that version is finalized in `docs/development/changelog.md`. Tagging is a maintainer decision, never part of a feature branch.
