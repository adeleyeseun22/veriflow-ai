# Background document processing

Phase 2C introduces a Celery worker using Redis database 1 as the broker and database 2 as the result backend. Redis database 0 remains reserved for application sessions and worker heartbeat state.

Each upload creates a `document_processing_jobs` record and transitions the document to `queued`. The worker then downloads the private MinIO object, recalculates its size and SHA-256 digest, and marks the document `ready` only when the stored object matches the upload metadata.

Transient object-storage failures use bounded exponential retries. Permanent integrity failures are recorded immediately. Failed documents can be manually requeued by workspace owners, administrators, and members. Worker heartbeats are stored in Redis with an expiry so the API readiness endpoint can detect a missing worker.

Phase 3 will build on this job framework for PDF, DOCX, spreadsheet, and CSV parsing.
