import csv
import hashlib
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import aiofiles
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from veriflow_api.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv"}
CANONICAL_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
}
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")
CHUNK_SIZE = 1024 * 1024


class UploadValidationError(ValueError):
    """Raised when an uploaded file fails validation."""


class UploadTooLargeError(UploadValidationError):
    """Raised when an upload exceeds the configured size limit."""


@dataclass(frozen=True, slots=True)
class StagedUpload:
    path: Path
    original_filename: str
    display_name: str
    extension: str
    mime_type: str
    size_bytes: int
    sha256: str
    client_content_type: str | None

    async def cleanup(self) -> None:
        await run_in_threadpool(self.path.unlink, missing_ok=True)


def sanitize_original_filename(filename: str | None) -> str:
    if not filename:
        raise UploadValidationError("A filename is required.")

    basename = filename.replace("\\", "/").split("/")[-1]
    normalized = unicodedata.normalize("NFKC", basename)
    cleaned = SAFE_FILENAME_PATTERN.sub("_", normalized).strip(" .")

    if not cleaned or cleaned in {".", ".."}:
        raise UploadValidationError("The filename is invalid.")

    path = Path(cleaned)
    suffix = path.suffix.lower()
    stem = path.stem.strip(" ._") or "document"
    maximum_stem_length = max(1, 255 - len(suffix))
    return f"{stem[:maximum_stem_length]}{suffix}"


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        supported = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise UploadValidationError(f"Unsupported file type. Allowed extensions: {supported}.")
    return extension


def display_name_from_filename(filename: str) -> str:
    return Path(filename).stem.replace("_", " ").strip() or "Untitled document"


def _validate_pdf(path: Path) -> None:
    with path.open("rb") as file_handle:
        header = file_handle.read(8)
        if not header.startswith(b"%PDF-"):
            raise UploadValidationError("The file does not contain a valid PDF signature.")

        file_handle.seek(max(0, path.stat().st_size - 2048))
        trailer = file_handle.read()
        if b"%%EOF" not in trailer:
            raise UploadValidationError("The PDF file is incomplete or malformed.")


def _validate_ooxml(path: Path, required_member: str, label: str) -> None:
    if not zipfile.is_zipfile(path):
        raise UploadValidationError(f"The file is not a valid {label} document.")

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or required_member not in names:
                raise UploadValidationError(f"The file is not a valid {label} document.")
    except zipfile.BadZipFile as error:
        raise UploadValidationError(f"The file is not a valid {label} document.") from error


def _validate_csv(path: Path) -> None:
    sample = path.read_bytes()[:262_144]
    if b"\x00" in sample:
        raise UploadValidationError("The CSV contains binary data.")

    try:
        text = sample.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise UploadValidationError("CSV files must use UTF-8 encoding.") from error

    if not text.strip():
        raise UploadValidationError("The CSV file does not contain readable data.")

    try:
        list(csv.reader(text.splitlines()[:20]))
    except csv.Error as error:
        raise UploadValidationError("The CSV structure could not be read.") from error


def validate_file_contents(path: Path, extension: str) -> str:
    if extension == ".pdf":
        _validate_pdf(path)
    elif extension == ".docx":
        _validate_ooxml(path, "word/document.xml", "DOCX")
    elif extension == ".xlsx":
        _validate_ooxml(path, "xl/workbook.xml", "XLSX")
    elif extension == ".csv":
        _validate_csv(path)
    else:
        raise UploadValidationError("Unsupported file type.")

    return CANONICAL_MIME_TYPES[extension]


async def stage_and_validate_upload(upload: UploadFile) -> StagedUpload:
    original_filename = sanitize_original_filename(upload.filename)
    extension = validate_extension(original_filename)
    temporary_file = NamedTemporaryFile(prefix="veriflow-upload-", suffix=extension, delete=False)
    temporary_path = Path(temporary_file.name)
    temporary_file.close()

    digest = hashlib.sha256()
    size_bytes = 0

    try:
        async with aiofiles.open(temporary_path, "wb") as destination:
            while chunk := await upload.read(CHUNK_SIZE):
                size_bytes += len(chunk)
                if size_bytes > settings.max_upload_size_bytes:
                    raise UploadTooLargeError(
                        "The file exceeds the "
                        f"{settings.max_upload_size_bytes // (1024 * 1024)} MB limit."
                    )
                digest.update(chunk)
                await destination.write(chunk)

        if size_bytes == 0:
            raise UploadValidationError("The uploaded file is empty.")

        mime_type = await run_in_threadpool(
            validate_file_contents,
            temporary_path,
            extension,
        )

        return StagedUpload(
            path=temporary_path,
            original_filename=original_filename,
            display_name=display_name_from_filename(original_filename),
            extension=extension.lstrip("."),
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=digest.hexdigest(),
            client_content_type=upload.content_type,
        )
    except Exception:
        await run_in_threadpool(temporary_path.unlink, missing_ok=True)
        raise
    finally:
        await upload.close()
