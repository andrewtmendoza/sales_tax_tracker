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

- Use short-lived branches from `develop`, for example `feature/offline-polish`, `fix/upload-errors`, or `docs/release-notes`.
- Pull requests targeting `develop` are the normal path for features, fixes, docs, and dependency updates.
- Pull requests targeting `main` are reserved for releases and must bump `version` in `pyproject.toml`.
- Release tags must match the version exactly in `vX.Y.Z` form.
- Pushing a matching release tag publishes a multi-arch GHCR image and creates a GitHub Release with generated notes.

Suggested flow:

1. Branch from `develop`
2. Open a PR back to `develop`
3. When `develop` is ready, open a release PR from `develop` to `main`
4. Bump `pyproject.toml` in the release PR
5. Merge the release PR
6. Push the signed release tag from `main`

Example release:

```bash
git tag -s v0.1.1 -m "v0.1.1"
git push origin v0.1.1
```

## Project Scope

This repo is intentionally scoped as a personal self-hosted app. Contributions that improve reliability, documentation, backup/restore, security, or tax-time workflows are the best fit.

Large multi-user platform features should start with an issue so the change in scope is discussed first.
