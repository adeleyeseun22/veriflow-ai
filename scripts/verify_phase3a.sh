#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

printf 'Checking API readiness...\n'
curl -fsS "$API_URL/health/ready" | python3 -m json.tool

printf 'Checking migration revision...\n'
docker compose exec -T postgres \
  psql -U veriflow -d veriflow -Atc \
  "SELECT version_num FROM alembic_version;" | grep -qx "20260629_0004"

printf 'Checking structured content tables...\n'
for table in document_pages document_sections document_tables; do
  docker compose exec -T postgres \
    psql -U veriflow -d veriflow -Atc \
    "SELECT to_regclass('public.${table}');" | grep -qx "$table"
done

printf 'Checking parser modules in the API container...\n'
docker compose exec -T api uv run --no-sync python - <<'PY'
from veriflow_api.parsers import parser_for_extension

for extension in ("pdf", "docx", "xlsx", "csv"):
    parser = parser_for_extension(extension)
    print(extension, parser.name, parser.version)
PY

printf 'Checking worker heartbeat...\n'
heartbeat="$(docker compose exec -T redis redis-cli GET veriflow:workers:document-processing)"
test -n "$heartbeat" && test "$heartbeat" != "(nil)"
printf 'Worker heartbeat: %s\n' "$heartbeat"

printf 'Phase 3A infrastructure verification passed.\n'
