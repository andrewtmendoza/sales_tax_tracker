.PHONY: install hooks lint test docker-up docker-dev

install:
	uv sync --dev

hooks:
	uv run pre-commit run --all-files

lint:
	uv run ruff check .

test:
	uv run pytest

docker-up:
	docker compose pull && docker compose up -d

docker-dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
