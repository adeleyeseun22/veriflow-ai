from veriflow_api.main import app
from veriflow_api.models import Base
from veriflow_api.models.processing_job import DocumentProcessingJob


def test_structured_content_models_are_registered() -> None:
    assert "document_pages" in Base.metadata.tables
    assert "document_sections" in Base.metadata.tables
    assert "document_tables" in Base.metadata.tables


def test_processing_jobs_default_to_structured_ingestion() -> None:
    job = DocumentProcessingJob()
    assert job.job_type is None or job.job_type == "structured_ingestion"


def test_structured_content_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    base = "/api/v1/workspaces/{workspace_id}/documents/{document_id}"
    assert f"{base}/content" in paths
    assert "get" in paths[f"{base}/content"]
    assert f"{base}/ingest" in paths
    assert "post" in paths[f"{base}/ingest"]
