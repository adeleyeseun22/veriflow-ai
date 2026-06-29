#!/usr/bin/env bash
set -euo pipefail

API_DIR="apps/api"

echo "Checking migration head..."
(
  cd "$API_DIR"
  uv run alembic current
)

echo "Checking document table..."
docker compose exec -T postgres \
  psql -U veriflow -d veriflow -c "\\d documents"

echo "Checking document statuses..."
docker compose exec -T postgres \
  psql -U veriflow -d veriflow \
  -c "SELECT unnest(enum_range(NULL::document_status));"

echo "Checking API routes..."
curl -fsS http://localhost:8000/openapi.json \
  | python3 -c '
import json
import sys

paths = json.load(sys.stdin)["paths"]
required = {
    "/api/v1/workspaces/{workspace_id}/documents",
    "/api/v1/workspaces/{workspace_id}/documents/check-duplicate",
    "/api/v1/workspaces/{workspace_id}/documents/{document_id}",
}
missing = required - paths.keys()
if missing:
    raise SystemExit(f"Missing routes: {sorted(missing)}")
print("Document routes verified.")
'

echo "Phase 2A verification passed."
