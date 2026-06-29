#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

required_files=(
  "apps/web/src/app/documents/[documentId]/page.tsx"
  "apps/web/src/app/documents/[documentId]/document-inspection.module.css"
  "apps/web/src/app/documents/page.tsx"
  "apps/web/src/lib/api.ts"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing Phase 3C file: $file" >&2
    exit 1
  fi
done

grep -q 'getDocumentContent' apps/web/src/lib/api.ts
grep -q 'listDocumentChunks' apps/web/src/lib/api.ts
grep -q 'queueStructuredIngestion' apps/web/src/lib/api.ts
grep -q 'href={`/documents/${document.id}`}' apps/web/src/app/documents/page.tsx
grep -q 'Processing history' 'apps/web/src/app/documents/[documentId]/page.tsx'

echo "Phase 3C source verification passed."
