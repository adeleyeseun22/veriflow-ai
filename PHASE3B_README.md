# VeriFlow AI Phase 3B — Structure-aware chunking

Phase 3B converts the pages, sections, and tables persisted in Phase 3A into deterministic retrieval units.

## Added capabilities

- section-aware text chunks;
- heading-path preservation;
- page-range references;
- table-aware row chunks;
- configurable text and table overlap;
- deterministic token estimates;
- stable SHA-256 chunk fingerprints;
- atomic replacement during re-ingestion;
- document-level chunk summaries;
- workspace-protected chunk-list API;
- migration `20260629_0005`;
- focused unit and route tests.

## Apply the package

From the VeriFlow repository root:

```bash
unzip -o ~/Downloads/VeriFlow_AI_Phase3B_Structure_Aware_Chunking.zip -d .
```

## Environment values

Set:

```env
API_VERSION=0.8.0
CHUNK_MAX_CHARS=4000
CHUNK_OVERLAP_CHARS=400
CHUNK_TABLE_MAX_ROWS=40
CHUNK_TABLE_ROW_OVERLAP=2
```

## Lock and install

The package intentionally does not replace `uv.lock`, because the local project already has a public-PyPI lock file. Update it locally:

```bash
cd apps/api
uv lock --python 3.12
uv sync --frozen --python 3.12 --group dev
```

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Expected test count after applying the package: approximately `45 passed`.

## Migration

With PostgreSQL running:

```bash
uv run alembic upgrade head
uv run alembic current
```

Expected revision:

```text
20260629_0005 (head)
```

## Rebuild services

From the repository root:

```bash
docker compose build api
docker compose up -d --force-recreate worker api
sleep 20
docker compose ps
```

## Verification

```bash
chmod +x scripts/verify_phase3b.sh
./scripts/verify_phase3b.sh
```

## Generate chunks

New uploads are parsed and chunked automatically. Existing Phase 3A documents can be reprocessed through:

```text
POST /api/v1/workspaces/{workspace_id}/documents/{document_id}/ingest
```

The final status message becomes:

```text
Structured content extracted and chunked for retrieval.
```

## Inspect chunks

```text
GET /api/v1/workspaces/{workspace_id}/documents/{document_id}/chunks
```

Supported query parameters:

- `limit`: 1–500;
- `offset`: 0 or greater;
- `source_type`: `section`, `page`, or `table`.

## Database inspection

```sql
SELECT
    d.original_filename,
    d.chunker_name,
    d.chunker_version,
    d.chunk_count,
    d.chunk_token_estimate,
    d.chunked_at
FROM documents d
ORDER BY d.created_at DESC;
```

```sql
SELECT
    d.original_filename,
    c.ordinal,
    c.source_type,
    c.source_label,
    c.heading_path,
    c.page_start,
    c.page_end,
    c.char_count,
    c.token_estimate,
    c.overlap_chars,
    LEFT(c.fingerprint, 12) AS fingerprint,
    LEFT(c.content, 160) AS preview
FROM document_chunks c
JOIN documents d ON d.id = c.document_id
ORDER BY d.created_at DESC, c.ordinal
LIMIT 50;
```

## Commit

```bash
git add .
git commit -m "feat: add structure-aware document chunking"
git push
```
