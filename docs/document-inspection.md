# Document inspection interface

The Phase 3C interface makes the ingestion pipeline observable to users without exposing database or worker internals.

## Inspection areas

### Overview

Shows source identity, SHA-256 integrity, file metadata, parser and chunker adapters, ingestion timestamps, the latest processing job, and captured document metadata.

### Pages

Shows extracted PDF page records with exact page numbering, character totals, word totals, and the persisted text used for downstream chunking.

### Sections

Shows detected headings, section paths, heading levels, page provenance, and section content.

### Tables

Shows extracted worksheet or document tables in a horizontally scrollable preview. The interface clearly identifies truncated previews.

### Chunks

Shows retrieval-ready chunks with source type, heading path, page range, token estimate, overlap size, and the stable SHA-256 chunk fingerprint. Users can filter by section, page, or table and search the loaded chunk set.

### Processing history

Shows every persisted ingestion job, its attempts, timestamps, status, and any recorded failure message.

## Permissions

Owners, administrators, and members may re-run structured ingestion. Reviewers have read-only access to inspection data.

## Loading limits

The view requests up to 200 pages, 200 sections, 100 tables, 50 rows per table preview, and 500 chunks. Database counts remain visible when a document exceeds these display limits.
