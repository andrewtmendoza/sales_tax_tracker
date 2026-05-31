# Sales Tax Tracker

Private self-hosted receipt capture and review app for tracking year-to-date sales tax from photographed receipts.

This project is intended for personal use. It supports mobile receipt capture, offline queueing on the capture screen, server-side image storage, and receipt field extraction through an OpenAI-compatible Responses API.

## What It Does

- Capture receipt photos from a phone-friendly web UI
- Queue captures locally when the phone is offline
- Upload receipt images to RustFS/S3-compatible storage
- Extract merchant, date, total, and sales tax through an OpenAI-compatible Responses endpoint
- Review and correct receipt metadata in a Django dashboard

## Tech Stack

- Backend: Django 5.1, Django Ninja
- Frontend: Django templates, HTMX, Alpine.js, Tailwind CSS, DaisyUI
- Data: PostgreSQL
- Object storage: RustFS / S3-compatible storage
- Receipt extraction: OpenAI-compatible Responses API
- Runtime: Docker Compose, Gunicorn, WhiteNoise
- Tooling: uv, pytest, Ruff, pre-commit, GitHub Actions

## Screenshots

### Mobile Capture

![Mobile capture screen](docs/screenshots/capture-mobile.png)

### Desktop Dashboard

![Desktop dashboard](docs/screenshots/dashboard-desktop.png)

## Deployment Model

- Use Docker Compose for normal deployment
- Use Django login for app authentication
- You can still put the app behind a reverse proxy
- Default web binding is `127.0.0.1:8000` so it is not exposed directly by default
- The default Compose file uses the latest published GHCR image
- Day-to-day work and dependency updates land on `develop` before release PRs move them to `main`

Do not expose this app directly to the public internet without understanding the security implications.

## Quick Start

1. Copy `.env.example` to `.env` and fill in real values.
2. Pull the latest published image and start the app:

```bash
docker pull ghcr.io/andrewtmendoza/sales_tax_tracker:latest
docker compose pull
docker compose up -d
```

3. Create a Django user in a second terminal:

```bash
docker compose exec web python manage.py createsuperuser
```

4. Open `http://127.0.0.1:8000/accounts/login/` and sign in.

5. Confirm the app is healthy:

```bash
curl http://127.0.0.1:8000/health/
```

## Offline iPhone Capture

If you want to capture receipts away from home and sync them later when your phone can reach the server again:

1. Open the app on your iPhone from a local address that reaches your server, such as `http://<local-ip>:8000/capture/` or your local-only domain.
2. Sign in and stay on `/capture/` until the page shows `Offline ready`.
3. Add that `/capture/` page to the Home Screen.
4. If the shortcut later opens while the server is unreachable, the app will fall back to the cached capture screen so new receipts can still be queued locally.

This offline mode is for receipt capture and later sync. The full dashboard still needs a reachable server.

## Required Configuration

The app will refuse to start unless these are configured:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `RECEIPT_LLM_RESPONSES_URL`
- `RECEIPT_LLM_API_KEY`
- `RECEIPT_LLM_MODEL`

OpenAI example:

```env
RECEIPT_LLM_RESPONSES_URL=https://api.openai.com/v1/responses
RECEIPT_LLM_API_KEY=sk-...
RECEIPT_LLM_MODEL=gpt-4.1-mini
```

## Reverse Proxy Notes

- Keep the container bound to loopback unless a trusted reverse proxy fronts it.
- Make sure the proxy forwards the correct `Host` header.
- Add your public hostname to `DJANGO_ALLOWED_HOSTS`.
- If your reverse proxy terminates TLS, set `DJANGO_TRUST_X_FORWARDED_PROTO=true` so Django treats forwarded HTTPS requests as secure.
- Set `DJANGO_SESSION_COOKIE_SECURE=true` and `DJANGO_CSRF_COOKIE_SECURE=true` for HTTPS deployments behind Traefik or another trusted proxy.
- Add your public `https://...` origin to `DJANGO_CSRF_TRUSTED_ORIGINS`.

Traefik-style example:

```env
DJANGO_ALLOWED_HOSTS=receipts.example.com
DJANGO_TRUST_X_FORWARDED_PROTO=true
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_CSRF_COOKIE_SECURE=true
DJANGO_CSRF_TRUSTED_ORIGINS=https://receipts.example.com
```

## Development

Install dependencies locally:

```bash
uv sync --dev
```

Install the browser used by Playwright E2E tests:

```bash
uv run playwright install chromium
```

Run tests:

```bash
uv run pytest
```

Run only the browser E2E tests:

```bash
uv run pytest -m e2e
```

Run hooks:

```bash
uv run pre-commit run --all-files
```

Use the development compose override for live code mounts and Django `runserver`:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

`docker-compose.yml` is the reference deployment configuration. `docker-compose.dev.yml` adds the local image build, bind mounts, and Django `runserver` for development.

Git branch flow:

- Feature, fix, docs, and dependency PRs target `develop` and normally use squash merge
- Release PRs target `main` and use merge commits
- Post-release sync PRs merge `main` back into `develop` with merge commits
- Only `main` is tagged for releases

## Releases

Manual releases are driven by signed Git tags and publish multi-arch images to GitHub Container Registry.

Release flow:

1. Merge day-to-day work into `develop`.
2. Open a release PR from `develop` to `main`.
3. Bump `version` in `pyproject.toml` in that release PR.
4. Merge the release PR to `main` with a merge commit so release ancestry stays visible.
5. If repository auto-merge is enabled, you can opt a release PR into automatic merge after checks pass:

```bash
gh pr merge --merge --auto --delete-branch
```

6. Create a signed tag that matches the version exactly:

```bash
git tag -s vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

If GitHub email privacy is enabled, create the signed tag with your GitHub noreply email as the tagger.

7. GitHub Actions will:
- verify the tag matches `pyproject.toml`
- build and push `linux/amd64` and `linux/arm64` images to GHCR
- verify the published multi-arch image can be inspected from GHCR
- create a GitHub Release with generated release notes

8. Sync `main` back into `develop` with a merge commit so `develop` retains the released ancestry for future comparisons.

```bash
gh pr merge --merge --auto --delete-branch
```

Published image:

```text
ghcr.io/andrewtmendoza/sales_tax_tracker
```

Tag `vX.Y.Z` publishes:

- `ghcr.io/andrewtmendoza/sales_tax_tracker:X.Y.Z`
- `ghcr.io/andrewtmendoza/sales_tax_tracker:X.Y`
- `ghcr.io/andrewtmendoza/sales_tax_tracker:X`
- `ghcr.io/andrewtmendoza/sales_tax_tracker:latest`
- `ghcr.io/andrewtmendoza/sales_tax_tracker:sha-<shortsha>`

You can inspect the published multi-arch image with:

```bash
docker buildx imagetools inspect ghcr.io/andrewtmendoza/sales_tax_tracker:X.Y.Z
```

## Versioning

- Pull requests targeting `main` must bump `pyproject.toml`.
- Pull requests targeting `develop` do not require a version bump.
- The release tag must match `pyproject.toml` exactly, using `vX.Y.Z`.
- Example: `version = "0.1.0"` requires the tag `v0.1.0`.

## Health Check

The app exposes a lightweight health endpoint at `/health/` for Docker and reverse proxy monitoring:

```bash
curl http://127.0.0.1:8000/health/
```

Expected response:

```json
{"status": "ok"}
```

## Backups

Back up Postgres:

```bash
docker compose exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

Back up RustFS data:

```bash
docker run --rm -v sales_tax_tracker_rustfs_data:/from -v "$PWD":/to alpine sh -c "cd /from && tar czf /to/rustfs-backup.tgz ."
```

## Privacy

- Receipt images are stored in your configured object storage.
- Raw model responses are stored in the database.
- When LLM extraction is enabled, receipt image data is sent to your configured model endpoint.

## Tax Disclaimer

This project helps organize receipt data. It does not provide tax, legal, or accounting advice.

## Repository Hygiene

- CI runs GitHub Actions for hooks, tests, and Docker builds.
- See `SECURITY.md` for security reporting and deployment expectations.
- See `CONTRIBUTING.md` for development workflow details.
