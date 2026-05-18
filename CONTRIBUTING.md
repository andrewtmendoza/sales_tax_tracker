# Contributing

## Development Setup

1. Install dependencies:

```bash
uv sync --dev
```

2. Copy `.env.example` to `.env` and provide real values if you want to run the full app.

3. Start the development stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Checks

Run the same checks as CI before opening a pull request:

```bash
uv run pre-commit run --all-files
uv run pytest
docker build .
cp .env.example .env
docker compose config > /dev/null
docker compose -f docker-compose.yml -f docker-compose.dev.yml config > /dev/null
```

## Branch And Release Conventions

- Use short-lived branches from `main`, for example `feature/offline-polish`, `fix/upload-errors`, or `docs/release-notes`.
- Pull requests targeting `main` must bump `version` in `pyproject.toml`.
- Release tags must match the version exactly in `vX.Y.Z` form.
- Pushing a matching release tag publishes a multi-arch GHCR image and creates a GitHub Release with generated notes.

Example release:

```bash
git tag -s v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

## Project Scope

This repo is intentionally scoped as a personal self-hosted app. Contributions that improve reliability, documentation, backup/restore, security, or tax-time workflows are the best fit.

Large multi-user platform features should start with an issue so the change in scope is discussed first.
