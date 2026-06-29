#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
MINIO_URL="${MINIO_URL:-http://localhost:9000}"
COOKIE_JAR="$(mktemp)"
REGISTER_RESPONSE="$(mktemp)"
WORKSPACE_RESPONSE="$(mktemp)"
UPLOAD_RESPONSE="$(mktemp)"
LIST_RESPONSE="$(mktemp)"
DUPLICATE_RESPONSE="$(mktemp)"
SAMPLE_PDF="$(mktemp -t veriflow-phase2b).pdf"
TIMESTAMP="$(date +%s)"
EMAIL="phase2b-${TIMESTAMP}@example.com"
PASSWORD="VeriFlow-Phase2B-${TIMESTAMP}!"

cleanup() {
  rm -f \
    "$COOKIE_JAR" \
    "$REGISTER_RESPONSE" \
    "$WORKSPACE_RESPONSE" \
    "$UPLOAD_RESPONSE" \
    "$LIST_RESPONSE" \
    "$DUPLICATE_RESPONSE" \
    "$SAMPLE_PDF"
}
trap cleanup EXIT

printf '%%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%%%EOF\n' > "$SAMPLE_PDF"

echo "1/8 Checking MinIO"
curl --fail --silent --show-error "${MINIO_URL}/minio/health/live" > /dev/null

echo "2/8 Registering ${EMAIL}"
curl --fail-with-body --silent --show-error \
  -c "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"full_name\":\"Phase Two Uploader\",\"password\":\"${PASSWORD}\"}" \
  "${API_URL}/api/v1/auth/register" > "$REGISTER_RESPONSE"
python3 -m json.tool "$REGISTER_RESPONSE"

CSRF_TOKEN="$(awk '$6 == "veriflow_csrf" {print $7}' "$COOKIE_JAR" | tail -n 1)"
if [[ -z "$CSRF_TOKEN" ]]; then
  echo "CSRF cookie was not created." >&2
  exit 1
fi

echo "3/8 Creating a workspace"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  -H "X-CSRF-Token: ${CSRF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"organization_name":"VeriFlow Storage Verification","name":"Secure Documents"}' \
  "${API_URL}/api/v1/workspaces" > "$WORKSPACE_RESPONSE"
python3 -m json.tool "$WORKSPACE_RESPONSE"

WORKSPACE_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$WORKSPACE_RESPONSE")"

echo "4/8 Uploading a validated PDF"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  -H "X-CSRF-Token: ${CSRF_TOKEN}" \
  -F "file=@${SAMPLE_PDF};filename=phase2b-evidence.pdf;type=application/pdf" \
  "${API_URL}/api/v1/workspaces/${WORKSPACE_ID}/documents" > "$UPLOAD_RESPONSE"
python3 -m json.tool "$UPLOAD_RESPONSE"

python3 - "$UPLOAD_RESPONSE" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1]))
assert payload["status"] == "uploaded", payload
assert payload["storage_provider"] == "minio", payload
assert payload["storage_bucket"], payload
assert payload["storage_key"], payload
assert len(payload["sha256"]) == 64, payload
print("Stored document metadata verified.")
PY

echo "5/8 Listing workspace documents"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  "${API_URL}/api/v1/workspaces/${WORKSPACE_ID}/documents" > "$LIST_RESPONSE"
python3 -m json.tool "$LIST_RESPONSE"

python3 - "$LIST_RESPONSE" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1]))
assert payload["total"] == 1, payload
assert len(payload["items"]) == 1, payload
print("Document library verified.")
PY

echo "6/8 Confirming duplicate rejection"
HTTP_STATUS="$(curl --silent --show-error \
  -o "$DUPLICATE_RESPONSE" \
  -w '%{http_code}' \
  -b "$COOKIE_JAR" \
  -H "X-CSRF-Token: ${CSRF_TOKEN}" \
  -F "file=@${SAMPLE_PDF};filename=phase2b-evidence-copy.pdf;type=application/pdf" \
  "${API_URL}/api/v1/workspaces/${WORKSPACE_ID}/documents")"

if [[ "$HTTP_STATUS" != "409" ]]; then
  echo "Expected duplicate upload to return 409, received ${HTTP_STATUS}." >&2
  cat "$DUPLICATE_RESPONSE" >&2
  exit 1
fi
python3 -m json.tool "$DUPLICATE_RESPONSE"

echo "7/8 Confirming upload audit event"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  "${API_URL}/api/v1/workspaces/${WORKSPACE_ID}/audit-logs?limit=20" \
  | python3 -c '
import json
import sys

items = json.load(sys.stdin)
actions = {item["action"] for item in items}
assert "document.uploaded" in actions, actions
print("document.uploaded audit event verified.")
'

echo "8/8 Confirming API readiness"
curl --fail-with-body --silent --show-error \
  "${API_URL}/health/ready" | python3 -m json.tool

echo "Phase 2B verification passed."
