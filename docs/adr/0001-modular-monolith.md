# ADR 0001: Begin as a Modular Monolith

- **Status:** Accepted
- **Date:** 28 June 2026

## Context

VeriFlow AI will eventually contain ingestion, retrieval, evidence validation, contradiction analysis, reporting, evaluation, authentication, storage, and background-processing capabilities. Splitting these concerns into networked microservices during the first release would increase deployment, debugging, data-consistency, and observability costs before usage patterns are known.

## Decision

Begin with two deployable applications:

1. A Next.js web application.
2. A FastAPI backend organized into explicit internal modules.

PostgreSQL and Redis remain separate infrastructure services. Internal boundaries will be designed so high-load functions can later be extracted when measurements justify it.

## Consequences

### Positive

- Faster development and simpler local setup.
- Easier end-to-end testing and transaction management.
- Lower operational cost.
- Clear evolutionary path without speculative distribution.

### Trade-offs

- One backend deployment initially contains several business modules.
- Module boundaries require discipline and automated tests.
- Resource-intensive ingestion work will later require dedicated workers.
