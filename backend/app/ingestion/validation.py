"""Safe file validation and content hashing."""
import hashlib
from pathlib import Path

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".htm": "text/html",
}


def validate_file(path: Path, filename: str, declared_content_type: str) -> str:
    if not path.is_file():
        raise ValueError("Upload is missing.")
    if path.stat().st_size == 0:
        raise ValueError("Empty files cannot be ingested.")
    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds the 25 MiB upload limit.")
    suffix = Path(filename).suffix.lower()
    expected = ALLOWED_TYPES.get(suffix)
    if expected is None:
        raise ValueError("Unsupported file extension; upload PDF or HTML.")
    if suffix == ".pdf":
        if declared_content_type not in {"application/pdf", "application/octet-stream"}:
            raise ValueError("File extension and content type do not match.")
        with path.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise ValueError("File does not have a valid PDF signature.")
        return "application/pdf"
    if declared_content_type not in {"text/html", "application/xhtml+xml", "application/octet-stream"}:
        raise ValueError("File extension and content type do not match.")
    return "text/html"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
