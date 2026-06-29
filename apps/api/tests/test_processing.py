from pathlib import Path

from veriflow_api.main import app
from veriflow_api.models.processing_job import ProcessingJobStatus
from veriflow_api.services.processing import calculate_file_sha256, retry_delay_seconds


def test_processing_status_lifecycle() -> None:
    assert [status.value for status in ProcessingJobStatus] == [
        "queued",
        "processing",
        "retrying",
        "succeeded",
        "failed",
    ]


def test_retry_delay_uses_bounded_exponential_backoff() -> None:
    assert retry_delay_seconds(1) == 5
    assert retry_delay_seconds(2) == 10
    assert retry_delay_seconds(3) == 20
    assert retry_delay_seconds(10) == 60


def test_calculate_file_sha256(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_bytes(b"veriflow")
    assert (
        calculate_file_sha256(path)
        == "bca5add5473b6000ba18f06f3f0fdcf8fb7cf6abc4b47a6a3e3332c6ed2a775f"
    )


def test_processing_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    base = "/api/v1/workspaces/{workspace_id}/documents/{document_id}"
    assert f"{base}/jobs" in paths
    assert f"{base}/retry" in paths
    assert "post" in paths[f"{base}/retry"]
