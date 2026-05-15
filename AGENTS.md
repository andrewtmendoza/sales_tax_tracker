# AGENTS.md

## Commands
- Install dependencies with `uv sync --dev`.
- Run hooks with `uv run pre-commit run --all-files`; the repo pins a newer `pre-commit` than some global installs support.
- Run the full test suite with `uv run pytest`.
- Run one test file or case with `uv run pytest receipts/tests/test_ingest.py` or `uv run pytest receipts/tests/test_ingest.py::test_ingest_creates_receipt`.
- Start the full dev stack with `docker compose up --build`; the `web` service waits for Postgres/RustFS, runs `python manage.py migrate --noinput`, then starts Django on port `8000`.
- Create/apply migrations outside Docker with `uv run python manage.py makemigrations` and `uv run python manage.py migrate`.
- `pyrightconfig.json` exists, but `pyright` is not listed in `pyproject.toml`; do not assume `uv run pyright` works unless the tool is installed separately.

## Architecture
- This is a Django 5.1 app managed by `uv`; the project package is `salt_tracker` and the main app is `receipts`.
- HTML routes live in `receipts/urls.py`: dashboard at `/`, capture page at `/capture/`, manifest and service worker routes at the root.
- API routes use Django Ninja: `salt_tracker/api.py` mounts `receipts/api.py` under `/api/receipts`.
- Receipt upload flow is `receipts/api.py` -> `receipts/services/ingest.py` -> RustFS/S3 storage plus receipt extraction through a configurable Responses API endpoint.
- The server computes the SHA-256 dedupe hash from uploaded bytes; the capture UI does not send a client hash.
- The capture UI is offline-first: `static/receipts/capture.js` stores `File` objects in IndexedDB and uploads them with `XMLHttpRequest` so the phone can show upload progress.

## Runtime And Tests
- `salt_tracker/settings.py` loads `.env` from the repo root with `python-dotenv`.
- Normal runtime defaults to Postgres on `localhost`; tests use `salt_tracker.test_settings` from `pytest.ini` and switch to in-memory SQLite.
- Receipt extraction config is controlled by `RECEIPT_LLM_RESPONSES_URL`, `RECEIPT_LLM_API_KEY`, `RECEIPT_LLM_MODEL`, and `RECEIPT_LLM_TIMEOUT_SECONDS`.
- Tests mock storage/LLM boundaries where needed, so `uv run pytest` should not require RustFS, Postgres, or a live LLM gateway.
- Docker Compose provides Postgres, RustFS, a one-shot bucket initializer, and the Django web service. RustFS has separate internal and browser-facing endpoints: `RUSTFS_ENDPOINT_URL` and `RUSTFS_PUBLIC_ENDPOINT_URL`.

## Frontend Notes
- There is no Node build pipeline. Templates use CDN Tailwind, DaisyUI, HTMX, and Alpine from `templates/base.html`.
- `templates/receipts/capture.html` intentionally disables the HTMX script block and relies on Alpine plus `static/receipts/capture.js`.
