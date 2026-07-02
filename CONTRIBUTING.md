# Contributing to SQLAlchemy-Continuum

Thank you for considering a contribution! This document explains how to get
set up and what we expect from bug reports and pull requests.

## Reporting bugs

Open a [bug report](https://github.com/sqlalchemy-continuum/sqlalchemy-continuum/issues/new/choose)
and include:

- The SQLAlchemy-Continuum, SQLAlchemy, and Python versions you are using.
- The database backend and driver (e.g. PostgreSQL + psycopg2).
- A minimal, complete, verifiable example — a short script with the models,
  the `make_versioned()` call, and the operations that trigger the problem.
- The full stack trace, if there is one.

Reduce your example to the simplest possible case before filing; most of the
triage time on this project is spent reproducing issues.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) for environment management:

```bash
git clone https://github.com/sqlalchemy-continuum/sqlalchemy-continuum.git
cd sqlalchemy-continuum
uv venv
uv pip install -e . --group dev
uv run pre-commit install
```

## Running tests

Tests default to SQLite and need no external services:

```bash
DB=sqlite uv run pytest
```

To test against PostgreSQL or MySQL, start a local server and set `DB` to
`postgres`, `postgres-native`, or `mysql` (see `tests/__init__.py` for the
connection defaults). The full matrix (Python versions × SQLAlchemy 1.4/2.x)
runs via tox:

```bash
uv run tox
```

## Linting and formatting

Ruff handles linting, import sorting, and formatting:

```bash
uv run ruff check --fix
uv run ruff format
```

Pre-commit runs the same checks on every commit if you installed the hook.

## Documentation

The user guide lives in `docs/` and is built with
[Zensical](https://zensical.org):

```bash
uv run zensical serve   # live-reload preview at http://localhost:8000
uv run zensical build --clean --strict   # static build into site/
```

## Pull requests

- Doc fixes need no issue — just open the PR.
- Code fixes and features should link an issue that contains a complete
  example, and must include tests. A test that fails without the fix is
  strongly preferred.
- Add an entry to `CHANGES.rst` under an "Unreleased" heading, and mirror it
  in `docs/changelog.md`.

## Release process (maintainers)

See `RELEASE.md`. Releases published on GitHub trigger the `publish.yml`
workflow, which builds and uploads to PyPI via trusted publishing.
