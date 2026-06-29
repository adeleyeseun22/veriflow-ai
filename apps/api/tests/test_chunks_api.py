from veriflow_api.main import app
from veriflow_api.models import Base, ChunkSourceType


def test_document_chunk_model_is_registered() -> None:
    assert "document_chunks" in Base.metadata.tables
    assert [source.value for source in ChunkSourceType] == ["section", "page", "table"]


def test_document_chunk_route_is_registered() -> None:
    path = "/api/v1/workspaces/{workspace_id}/documents/{document_id}/chunks"
    assert path in app.openapi()["paths"]
    assert "get" in app.openapi()["paths"][path]
