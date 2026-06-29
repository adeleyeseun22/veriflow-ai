# VeriFlow AI Phase 2B

This package adds secure document uploads and MinIO object storage.

## Added

- PDF, DOCX, XLSX, and CSV validation
- 25 MB default upload limit
- Streaming SHA-256 calculation
- Workspace-scoped duplicate rejection
- Private MinIO object storage
- Upload permissions and CSRF protection
- `document.uploaded` audit events
- Document library frontend
- Object-storage readiness check
- Unit tests and an end-to-end verification script

No document parsing or background worker is included yet. Those belong to Phase 2C.
