#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

printf '\n[1/6] Checking API readiness...\n'
readiness="$(curl -fsS "${API_URL}/health/ready")"
printf '%s\n' "$readiness" | python3 -m json.tool
printf '%s' "$readiness" | grep -q '"version":"0.8.0"\|"version": "0.8.0"'
printf '%s' "$readiness" | grep -q '"document_worker":"healthy"\|"document_worker": "healthy"'

printf '\n[2/6] Checking Alembic revision...\n'
docker compose exec -T api uv run --no-sync alembic current | grep -q '20260629_0005'

printf '\n[3/6] Checking chunk table...\n'
docker compose exec -T postgres \
  psql -U veriflow -d veriflow -Atc \
  "SELECT to_regclass('public.document_chunks');" | grep -q 'document_chunks'

printf '\n[4/6] Checking chunk source enum...\n'
enum_values="$(docker compose exec -T postgres \
  psql -U veriflow -d veriflow -Atc \
  "SELECT unnest(enum_range(NULL::chunk_source_type));")"
printf '%s\n' "$enum_values"
printf '%s\n' "$enum_values" | grep -q 'SECTION'
printf '%s\n' "$enum_values" | grep -q 'PAGE'
printf '%s\n' "$enum_values" | grep -q 'TABLE'

printf '\n[5/6] Checking worker heartbeat...\n'
heartbeat="$(docker compose exec -T redis \
  redis-cli GET veriflow:workers:document-processing | tr -d '\r')"
test -n "$heartbeat"
test "$heartbeat" != "(nil)"
printf 'Worker heartbeat: %s\n' "$heartbeat"

printf '\n[6/6] Checking OpenAPI chunk route...\n'
curl -fsS "${API_URL}/openapi.json" \
  | grep -q '/api/v1/workspaces/{workspace_id}/documents/{document_id}/chunks'

printf '\nPhase 3B infrastructure verification passed.\n'
printf 'Re-ingest or upload a document, then confirm document_chunks contains records.\n'
