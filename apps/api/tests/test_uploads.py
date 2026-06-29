import zipfile
from pathlib import Path

import pytest

from veriflow_api.main import app
from veriflow_api.services.uploads import (
    UploadValidationError,
    display_name_from_filename,
    sanitize_original_filename,
    validate_extension,
    validate_file_contents,
)


def test_sanitize_original_filename_removes_paths_and_unsafe_characters() -> None:
    assert sanitize_original_filename("../../Quarterly Report?.PDF") == "Quarterly Report.pdf"
    assert sanitize_original_filename(r"C:\\files\\budget.xlsx") == "budget.xlsx"


def test_validate_extension_accepts_supported_types() -> None:
    assert validate_extension("report.pdf") == ".pdf"
    assert validate_extension("data.CSV") == ".csv"


def test_validate_extension_rejects_unsupported_types() -> None:
    with pytest.raises(UploadValidationError, match="Unsupported file type"):
        validate_extension("payload.exe")


def test_display_name_is_readable() -> None:
    assert display_name_from_filename("quarterly_report.csv") == "quarterly report"


def test_validate_pdf_signature(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n")

    assert validate_file_contents(pdf_path, ".pdf") == "application/pdf"


def test_validate_csv_content(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")

    assert validate_file_contents(csv_path, ".csv") == "text/csv"


def test_validate_docx_structure(tmp_path: Path) -> None:
    docx_path = tmp_path / "sample.docx"
    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<document />")

    expected = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert validate_file_contents(docx_path, ".docx") == expected


def test_invalid_pdf_is_rejected(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.pdf"
    invalid_path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(UploadValidationError, match="PDF signature"):
        validate_file_contents(invalid_path, ".pdf")


def test_upload_route_is_registered() -> None:
    route = app.openapi()["paths"]["/api/v1/workspaces/{workspace_id}/documents"]
    assert "post" in route
    assert "get" in route
