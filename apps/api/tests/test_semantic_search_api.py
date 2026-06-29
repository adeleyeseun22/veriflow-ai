from pgvector.sqlalchemy import Vector

from veriflow_api.main import app
from veriflow_api.models import Base


def test_vector_embedding_columns_are_registered() -> None:
    chunks = Base.metadata.tables["document_chunks"]
    documents = Base.metadata.tables["documents"]

    assert isinstance(chunks.c.embedding.type, Vector)
    assert chunks.c.embedding_provider is not None
    assert chunks.c.embedding_model is not None
    assert documents.c.embedding_count is not None
    assert documents.c.embedding_dimension is not None


def test_semantic_search_route_is_registered() -> None:
    path = "/api/v1/workspaces/{workspace_id}/search/semantic"

    assert path in app.openapi()["paths"]
    assert "get" in app.openapi()["paths"][path]
