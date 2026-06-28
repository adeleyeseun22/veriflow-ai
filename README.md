# VeriFlow AI

VeriFlow AI is a multimodal evidence, data, and decision intelligence platform. The Phase 0 foundation provides a modern Next.js frontend, a FastAPI backend, PostgreSQL with pgvector, Redis, Docker Compose, automated tests, and CI.

## Current phase

**Phase 0 — Product foundation and local infrastructure**

## Services

| Service | URL | Purpose |
|---|---|---|
| Web | http://localhost:3000 | Next.js product interface |
| API | http://localhost:8000 | FastAPI application API |
| API docs | http://localhost:8000/docs | OpenAPI/Swagger documentation |
| PostgreSQL | localhost:5432 | Relational data and vector search |
| Redis | localhost:6379 | Cache and background-job infrastructure |

## Quick start

```bash
cp .env.example .env
corepack enable
pnpm install
cd apps/api && uv sync --group dev && cd ../..
docker compose up --build -d
```

Then verify:

```bash
docker compose ps
make health
```

## Development checks

```bash
make lint
make test
```

## Architecture

See `docs/architecture.md`, `docs/product-requirements.md`, and `docs/adr/0001-modular-monolith.md`.
