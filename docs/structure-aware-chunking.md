# Structure-aware chunking

Phase 3B converts persisted pages, sections, and tables into deterministic retrieval units.

## Chunk sources

VeriFlow stores three chunk source types:

- `section`: heading-aware narrative text from DOCX, PDF page sections, worksheets, and CSV bodies.
- `page`: a fallback used only when a document has extractable pages but no text-bearing sections.
- `table`: row-aware serializations that preserve column names, table labels, row ranges, and truncation metadata.

## Boundaries and overlap

Narrative text is split near paragraph, line, sentence, punctuation, or word boundaries. The default maximum is 4,000 characters with 400 characters of overlap. Table chunks use row boundaries, repeat the table heading and columns, and retain two overlapping rows by default.

The overlap is recorded on each chunk so later retrieval and answer generation can deduplicate adjacent context.

## Provenance

Each chunk stores:

- document, section, and table relationships;
- source type and label;
- heading path;
- page range;
- source ordinal and part index;
- character, word, and estimated token counts;
- overlap size;
- a stable SHA-256 fingerprint;
- source-specific metadata.

Fingerprints use stable source ordinals and content rather than database UUIDs. Reprocessing unchanged content therefore regenerates the same fingerprints even though section and table records are replaced.

## Replacement semantics

Structured ingestion replaces all existing chunks for a document in the same database transaction that stores the newly parsed structure. This prevents stale retrieval units from surviving a re-ingestion.

## Token estimates

Phase 3B uses a deterministic, model-agnostic estimate based on both character and word counts. A model-specific tokenizer will be introduced when embedding providers are configured.

## Retrieval readiness

A document is marked `ready` only after:

1. object integrity verification;
2. structured parsing;
3. structured-content persistence;
4. chunk generation;
5. chunk persistence.

The final status message is `Structured content extracted and chunked for retrieval.`
