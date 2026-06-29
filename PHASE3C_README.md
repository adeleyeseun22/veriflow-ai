# VeriFlow AI — Phase 3C

Phase 3C adds the document inspection experience for the structured-ingestion pipeline.

## Included

- Document detail route: `/documents/[documentId]`
- Page, section, table, chunk, and processing-history views
- Chunk search and source-type filtering
- Parser and chunker summaries
- Source integrity and metadata panels
- Structured-ingestion rerun control
- Live status polling while a document is processing
- Direct **Inspect** links from the document library
- Extended frontend API types and client functions

## Backend impact

No database migration and no backend image rebuild are required. Phase 3C uses the APIs introduced in Phases 2C, 3A, and 3B.

## Required validation

```bash
pnpm lint:web
pnpm typecheck:web
pnpm build:web
```

Then start the frontend and inspect a ready document:

```bash
pnpm --filter @veriflow/web dev
```

Open `http://localhost:3000/documents`, select **Inspect**, and validate every inspection tab.
