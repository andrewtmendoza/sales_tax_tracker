.PHONY: install hooks lint test docker-up

install:
	uv sync --dev

hooks:
	uv run pre-commit run --all-files

lint:
	uv run ruff check .

test:
	uv run pytest

docker-up:
	docker compose up --build
