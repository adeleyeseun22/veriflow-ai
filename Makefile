SHELL := /bin/bash

.PHONY: help install env up down restart logs ps test lint format health clean

help:
	@echo "VeriFlow AI development commands"
	@echo "  make install   Install frontend and backend dependencies"
	@echo "  make env       Create .env from .env.example when missing"
	@echo "  make up        Build and start all Docker services"
	@echo "  make down      Stop Docker services"
	@echo "  make restart   Restart Docker services"
	@echo "  make logs      Follow all Docker logs"
	@echo "  make ps        Show Docker service status"
	@echo "  make health    Call frontend and API health endpoints"
	@echo "  make test      Run backend tests and frontend type checks"
	@echo "  make lint      Run backend and frontend linters"
	@echo "  make format    Format backend code"
	@echo "  make clean     Remove generated local build artifacts"

install:
	corepack enable
	pnpm install
	cd apps/api && uv sync --group dev

env:
	@test -f .env || cp .env.example .env
	@echo ".env is ready"

up: env
	docker compose up --build -d

down:
	docker compose down

restart:
	docker compose down
	docker compose up --build -d

logs:
	docker compose logs -f

ps:
	docker compose ps

health:
	@echo "API liveness:"
	@curl --fail --silent http://localhost:8000/health/live | python3 -m json.tool
	@echo "API readiness:"
	@curl --fail --silent http://localhost:8000/health/ready | python3 -m json.tool
	@echo "Frontend:"
	@curl --fail --silent --output /dev/null --write-out "%{http_code}\n" http://localhost:3000

test:
	cd apps/api && uv run pytest
	pnpm typecheck:web

lint:
	cd apps/api && uv run ruff check .
	pnpm lint:web

format:
	cd apps/api && uv run ruff format .

clean:
	rm -rf apps/web/.next apps/web/node_modules node_modules
	rm -rf apps/api/.venv apps/api/.pytest_cache apps/api/.ruff_cache
