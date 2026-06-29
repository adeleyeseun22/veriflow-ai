#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

printf 'Checking API version and health...\n'
health="$(curl -fsS "$API_URL/health/ready")"
printf '%s\n' "$health" | python3 -m json.tool
printf '%s' "$health" | grep -q '"version":"0.9.0"' || \
  printf '%s' "$health" | grep -q '"version": "0.9.0"'

printf 'Checking Alembic revision...\n'
revision="$(docker compose exec -T postgres psql -U veriflow -d veriflow -Atc \
  'SELECT version_num FROM alembic_version;')"
test "$revision" = "20260629_0006"

printf 'Checking pgvector extension...\n'
docker compose exec -T postgres psql -U veriflow -d veriflow -Atc \
  "SELECT extversion FROM pg_extension WHERE extname = 'vector';" | grep -q .

printf 'Checking vector column and HNSW index...\n'
docker compose exec -T postgres psql -U veriflow -d veriflow -Atc \
  "SELECT data_type FROM information_schema.columns WHERE table_name = 'document_chunks' AND column_name = 'embedding';" | grep -q 'USER-DEFINED'
docker compose exec -T postgres psql -U veriflow -d veriflow -Atc \
  "SELECT indexname FROM pg_indexes WHERE tablename = 'document_chunks' AND indexname = 'ix_document_chunks_embedding_hnsw';" | grep -q 'ix_document_chunks_embedding_hnsw'

printf 'Checking semantic search route...\n'
curl -fsS "$API_URL/openapi.json" | grep -q \
  '/api/v1/workspaces/{workspace_id}/search/semantic'

printf 'Checking worker heartbeat...\n'
docker compose exec -T redis redis-cli GET \
  veriflow:workers:document-processing | grep -qv '(nil)'

printf 'Phase 4A infrastructure verification passed.\n'
