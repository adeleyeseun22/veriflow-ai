#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
COOKIE_JAR="$(mktemp)"
REGISTER_RESPONSE="$(mktemp)"
WORKSPACE_RESPONSE="$(mktemp)"
TIMESTAMP="$(date +%s)"
EMAIL="phase1b-${TIMESTAMP}@example.com"
PASSWORD="VeriFlow-Phase1B-${TIMESTAMP}!"

cleanup() {
  rm -f "$COOKIE_JAR" "$REGISTER_RESPONSE" "$WORKSPACE_RESPONSE"
}
trap cleanup EXIT

echo "1/7 Registering ${EMAIL}"
curl --fail-with-body --silent --show-error \
  -c "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"full_name\":\"Phase One Reviewer\",\"password\":\"${PASSWORD}\"}" \
  "${API_URL}/api/v1/auth/register" > "$REGISTER_RESPONSE"
python3 -m json.tool "$REGISTER_RESPONSE"

CSRF_TOKEN="$(awk '$6 == "veriflow_csrf" {print $7}' "$COOKIE_JAR" | tail -n 1)"
if [[ -z "$CSRF_TOKEN" ]]; then
  echo "CSRF cookie was not created." >&2
  exit 1
fi

echo "2/7 Reading the authenticated user"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  "${API_URL}/api/v1/auth/me" | python3 -m json.tool

echo "3/7 Creating the first workspace"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  -H "X-CSRF-Token: ${CSRF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"organization_name":"VeriFlow Demo Organization","name":"Evidence Operations"}' \
  "${API_URL}/api/v1/workspaces" > "$WORKSPACE_RESPONSE"
python3 -m json.tool "$WORKSPACE_RESPONSE"

WORKSPACE_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$WORKSPACE_RESPONSE")"

echo "4/7 Listing accessible workspaces"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  "${API_URL}/api/v1/workspaces" | python3 -m json.tool

echo "5/7 Reading the workspace as its owner"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  "${API_URL}/api/v1/workspaces/${WORKSPACE_ID}" | python3 -m json.tool

echo "6/7 Reading the workspace audit trail"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  "${API_URL}/api/v1/workspaces/${WORKSPACE_ID}/audit-logs" | python3 -m json.tool

echo "7/7 Signing out"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" \
  -H "X-CSRF-Token: ${CSRF_TOKEN}" \
  -X POST \
  "${API_URL}/api/v1/auth/logout" | python3 -m json.tool

echo "Phase 1B verification passed."
