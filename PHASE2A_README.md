# VeriFlow AI Phase 2A

This package adds the document metadata and duplicate-detection foundation.

## Added

- `Document` SQLAlchemy model
- `DocumentStatus` lifecycle enum
- Workspace-scoped SHA-256 uniqueness
- Storage locator fields
- Processing status and retry metadata
- Document list, detail, and duplicate-check APIs
- Alembic revision `20260629_0002`
- Unit tests and verification script

No object-storage service or upload endpoint is included yet; those belong to Phase 2B.
