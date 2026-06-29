import pytest

from veriflow_api.main import app
from veriflow_api.models.document import DocumentStatus
from veriflow_api.services.documents import normalize_sha256


def test_document_status_lifecycle() -> None:
    assert [status.value for status in DocumentStatus] == [
        "pending",
        "uploaded",
        "queued",
        "processing",
        "ready",
        "failed",
    ]


def test_normalize_sha256() -> None:
    uppercase_hash = "A" * 64
    assert normalize_sha256(f"  {uppercase_hash}  ") == "a" * 64


@pytest.mark.parametrize(
    "value",
    [
        "",
        "abc",
        "g" * 64,
        "a" * 63,
        "a" * 65,
    ],
)
def test_normalize_sha256_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="64 hexadecimal"):
        normalize_sha256(value)


def test_document_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/workspaces/{workspace_id}/documents" in paths
    assert "/api/v1/workspaces/{workspace_id}/documents/check-duplicate" in paths
    assert "/api/v1/workspaces/{workspace_id}/documents/{document_id}" in paths
