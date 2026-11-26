from pathlib import Path
import pytest
from app.ingestion.validation import validate_file, sha256_file
from app.ingestion.extractors import extract_document


def test_pdf_signature_and_hash(tmp_path):
    p = tmp_path / "sample.pdf"
    p.write_bytes(b"%PDF-1.7 sample")
    assert validate_file(p, "sample.pdf", "application/pdf") == "application/pdf"
    assert len(sha256_file(p)) == 64


def test_reject_extension_mismatch(tmp_path):
    p = tmp_path / "sample.exe"
    p.write_bytes(b"not a pdf")
    with pytest.raises(ValueError):
        validate_file(p, "sample.exe", "application/pdf")


def test_html_extraction_removes_script(tmp_path):
    p = tmp_path / "sample.html"
    p.write_text("<html><script>secret()</script><body><h1>Section 1</h1><p>Legal text</p></body></html>")
    result = extract_document(p, "text/html")
    assert "Section 1" in result.text
    assert "secret" not in result.text
