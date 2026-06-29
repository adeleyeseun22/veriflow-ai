# Semantic retrieval

Phase 4A stores one normalized 384-dimensional vector for every structured document chunk.
The default provider is FastEmbed with `BAAI/bge-small-en-v1.5`. The API and worker share a
persistent model-cache volume so the model is downloaded only once per local Docker project.

## Retrieval namespace

Every vector records its provider and model. Search only compares query vectors with chunk
vectors from the same namespace. Changing the embedding model therefore requires re-ingesting
existing documents before they appear in results for the new model.

## Index

PostgreSQL uses an HNSW index with cosine distance on non-null chunk embeddings. The semantic
search endpoint is workspace-scoped and supports document and source-type filters.

## Endpoint

`GET /api/v1/workspaces/{workspace_id}/search/semantic`

Query parameters:

- `q`: required search question or phrase
- `limit`: 1–50 results
- `min_score`: cosine similarity threshold from -1 to 1
- `document_id`: optional document restriction
- `source_type`: optional `section`, `page`, or `table` restriction
