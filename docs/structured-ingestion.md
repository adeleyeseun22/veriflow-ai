# Structured document ingestion

Phase 3A extends the background worker from integrity verification into structured extraction.

## Supported formats

- PDF: page-level text through pypdf.
- DOCX: headings, paragraphs, and native Word tables through python-docx.
- XLSX: worksheet sections and bounded table extraction through openpyxl.
- CSV: dialect-aware UTF-8 table extraction through Python's csv module.

## Persistence

Structured content is stored in three workspace-owned document resources:

- `document_pages`
- `document_sections`
- `document_tables`

Each processing run replaces the previous extracted structure transactionally. The original object in MinIO remains unchanged and continues to be the source of truth.

## Resource limits

Parser limits cap PDF pages, table rows and columns, cell lengths, and section text. These limits reduce accidental memory exhaustion and prevent unbounded JSON responses. PDF OCR and advanced visual table extraction are intentionally outside Phase 3A.
