# Document Lifecycle

Phase 2A introduces the logical document record and its processing lifecycle.

## Statuses

- `pending`: metadata has been prepared but storage is not yet confirmed.
- `uploaded`: the original file is safely stored.
- `queued`: background processing has been requested.
- `processing`: a worker is actively processing the file.
- `ready`: processing completed successfully.
- `failed`: processing stopped with a recorded failure message.

## Duplicate policy

A SHA-256 fingerprint is unique within a workspace. The same file may exist in different
workspaces, but an exact duplicate cannot be registered twice inside one workspace.

## Storage fields

`storage_provider`, `storage_bucket`, and `storage_key` are nullable in Phase 2A. Phase 2B will
populate them after secure object storage succeeds.
