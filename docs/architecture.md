# VeriFlow AI Architecture — Phase 0

## Architectural style

VeriFlow AI begins as a modular monolith. This preserves clear service boundaries without introducing premature distributed-system complexity.

## Runtime components

```text
Browser
  |
  v
Next.js web application :3000
  |
  v
FastAPI application :8000
  |-------------------|
  v                   v
PostgreSQL :5432      Redis :6379
+ pgvector            cache / queues
```

## Initial boundaries

- `apps/web`: product interface and browser-facing interactions.
- `apps/api`: API, configuration, persistence adapters, cache adapters, and future agent workflows.
- `infrastructure`: local containers and database initialization.
- `docs`: architectural decisions and implementation notes.

## Phase 0 quality gates

- All containers become healthy.
- The API liveness endpoint responds without external dependencies.
- The API readiness endpoint verifies PostgreSQL and Redis.
- Backend tests pass.
- Frontend linting, type checking, and production build pass.
- CI repeats those checks for every push and pull request.

## Planned evolution

Later phases add authentication, workspace tenancy, document ingestion, object storage, hybrid retrieval, reranking, claim-level citations, validation workflows, contradiction detection, evaluation, observability, and cloud deployment.
