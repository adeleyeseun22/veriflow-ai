# VeriFlow AI Product Requirements — MVP Baseline

## Product statement

VeriFlow AI is an evidence, data, and decision intelligence platform that converts mixed organizational information into traceable answers, validated findings, and reviewable reports.

## Primary users

- Analysts who reconcile reports, spreadsheets, contracts, and meeting records.
- Reviewers who must approve or reject AI-generated findings.
- Managers who need defensible summaries, risks, obligations, and decisions.
- Technical teams responsible for knowledge systems, data quality, and AI governance.

## MVP workflow

```text
Upload documents and spreadsheets
→ Parse and index them
→ Ask a cross-document question
→ Retrieve and rerank evidence
→ Generate a cited answer
→ Validate material claims
→ Detect a numerical discrepancy or contradiction
→ Route the finding to human review
→ Measure quality
→ Export an approved report
```

## MVP functional requirements

1. A user can authenticate and create a workspace.
2. A user can upload PDF, DOCX, XLSX, and CSV files.
3. The platform extracts document structure and spreadsheet records.
4. The platform performs hybrid lexical and vector retrieval.
5. Generated answers contain exact evidence citations.
6. The platform identifies insufficient evidence instead of inventing an answer.
7. Numerical statements can be compared with structured source data.
8. Cross-document conflicts can be surfaced with version and date context.
9. Human reviewers can approve, reject, annotate, and resolve findings.
10. Evaluation runs report retrieval, grounding, validation, latency, and cost metrics.
11. Approved outputs can be exported.
12. Every material result is represented in an audit trail.

## Phase 0 requirements

- Reproducible local environment.
- Next.js frontend.
- FastAPI backend.
- PostgreSQL 18 with pgvector.
- Redis.
- Liveness and readiness endpoints.
- Automated linting, type checking, tests, and production builds.
- Docker Compose orchestration.
- GitHub Actions CI.

## Non-functional requirements

- Clear module boundaries without premature microservices.
- Typed interfaces in Python and TypeScript.
- Secure environment-variable handling.
- Health checks for required infrastructure.
- Repeatable dependency locks.
- Accessible and responsive user interface.
- Testable deterministic logic where an LLM is not required.
- Synthetic public demo data only.
- Observable errors and explicit failure states.

## Explicitly out of scope for Phase 0

- Authentication implementation.
- Document upload and object storage.
- Embeddings and retrieval.
- LLM providers.
- LangGraph workflows.
- Background workers.
- Report exports.
- Production cloud resources.

These are introduced in later phases after the foundation passes its quality gates.
