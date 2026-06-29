#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

echo "Checking API readiness, including the document worker..."
curl --fail --silent "$API_URL/health/ready" | python3 -m json.tool

echo "Checking the processing table..."
docker compose exec -T postgres psql -U veriflow -d veriflow -c "\d document_processing_jobs"

echo "Checking worker heartbeat..."
docker compose exec -T redis redis-cli GET veriflow:workers:document-processing

echo "Phase 2C infrastructure verification passed."
