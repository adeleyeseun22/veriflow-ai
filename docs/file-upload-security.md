# Secure File Upload and Object Storage

Phase 2B introduces the first production-oriented upload path for VeriFlow AI.

## Supported formats

- PDF
- DOCX
- XLSX
- CSV encoded as UTF-8

The browser's MIME type is recorded for audit purposes but is never trusted as the source of truth.
The API validates each file using its extension and internal structure:

- PDF files must contain a PDF header and end marker.
- DOCX files must be valid ZIP containers with Word document members.
- XLSX files must be valid ZIP containers with Excel workbook members.
- CSV files must contain readable UTF-8 text and no null bytes.

## Size control

Uploads are streamed to a temporary file in one-megabyte chunks. Processing stops as soon as the
configured limit is exceeded. The default limit is 25 MB.

## File identity

A SHA-256 fingerprint is calculated during streaming. The database enforces uniqueness for the
combination of workspace and fingerprint, preventing the exact same file from being stored twice in
one workspace.

## Object naming

Original filenames are normalized before storage. Files are stored under a generated object path:

```text
workspaces/{workspace_id}/documents/{document_id}/{safe_filename}
```

The MinIO bucket is private. Files are not exposed through public URLs.

## Authorization

- Owners, administrators, and members can upload.
- Reviewers can view the document library but cannot upload.
- Upload requests require an authenticated session and a valid CSRF token.
- Every successful upload creates a `document.uploaded` audit event.

## Failure handling

The database record is created only after object storage succeeds. If the database transaction then
fails, VeriFlow removes the object to avoid orphaned files. Temporary files are deleted after every
request, whether the request succeeds or fails.
