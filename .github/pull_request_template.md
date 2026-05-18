## Summary

-

## Verification

- [ ] `uv run pytest`
- [ ] `uv run pre-commit run --all-files`
- [ ] `docker build .`
- [ ] `docker compose --env-file .env.example config`
- [ ] `docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.dev.yml config`

## Release Notes

- [ ] This PR targets `develop` and does not need a version bump
- [ ] This PR targets `main` and includes the required `pyproject.toml` version bump
