import hashlib
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.ingestion import IngestionChunk, IngestionJob
from app.evidence.provenance import verify_chunk_evidence

def _records(db, file_path):
    raw = file_path.read_bytes()
    job = IngestionJob(
        id="job-1", filename="judgment.pdf",
        content_sha256=hashlib.sha256(raw).hexdigest(),
        content_type="application/pdf", status="extracted",
        storage_key="originals/judgment.pdf", source_name="Court website",
        source_url="https://example.invalid/judgment.pdf", source_class="primary",
    )
    chunk = IngestionChunk(
        id="chunk-1", job_id="job-1", ordinal=1, chunk_type="judgment_paragraph",
        locator="Paragraph 12", heading="Issue", body_text="The appeal is allowed.",
        page_start=12, page_end=12,
    )
    db.add_all([job, chunk])
    db.commit()

def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)

def test_verifies_real_chunk_original_hash_locator_and_text(tmp_path):
    (tmp_path / "originals").mkdir()
    (tmp_path / "originals" / "judgment.pdf").write_bytes(b"%PDF-1.7 test bytes")
    with _session() as db:
        _records(db, tmp_path / "originals" / "judgment.pdf")
        result = verify_chunk_evidence(
            db, chunk_id="chunk-1", storage_root=tmp_path,
            expected_page=12, expected_locator="Paragraph 12",
            supplied_text="The appeal is allowed.",
        )
    assert result["status"] == "verified"
    assert result["integrity_status"] == "matched"
    assert result["locator_status"] == "matched"
    assert result["text_status"] == "matched"

def test_missing_original_is_partial_not_verified(tmp_path):
    with _session() as db:
        # DB row contains a plausible hash but original file is not present.
        job = IngestionJob(
            id="job-1", filename="judgment.pdf", content_sha256="a" * 64,
            content_type="application/pdf", status="extracted",
            storage_key="originals/missing.pdf",
        )
        chunk = IngestionChunk(
            id="chunk-1", job_id="job-1", ordinal=1, chunk_type="paragraph",
            body_text="Stored passage", page_start=1, page_end=1,
        )
        db.add_all([job, chunk]); db.commit()
        result = verify_chunk_evidence(db, chunk_id="chunk-1", storage_root=tmp_path)
    assert result["status"] == "partially_verified"
    assert result["integrity_status"] == "unavailable"

def test_modified_original_is_unresolved(tmp_path):
    (tmp_path / "originals").mkdir()
    original = tmp_path / "originals" / "judgment.pdf"
    original.write_bytes(b"original")
    with _session() as db:
        _records(db, original)
        original.write_bytes(b"tampered")
        result = verify_chunk_evidence(db, chunk_id="chunk-1", storage_root=tmp_path)
    assert result["status"] == "unresolved"
    assert result["integrity_status"] == "mismatch"

def test_wrong_page_or_text_is_unresolved(tmp_path):
    (tmp_path / "originals").mkdir()
    original = tmp_path / "originals" / "judgment.pdf"
    original.write_bytes(b"%PDF-1.7 test bytes")
    with _session() as db:
        _records(db, original)
        result = verify_chunk_evidence(
            db, chunk_id="chunk-1", storage_root=tmp_path,
            expected_page=99, supplied_text="A different passage.",
        )
    assert result["status"] == "unresolved"
    assert result["locator_status"] == "mismatch"
    assert result["text_status"] == "mismatch"

def test_unknown_chunk_is_unresolved(tmp_path):
    with _session() as db:
        result = verify_chunk_evidence(db, chunk_id="not-a-real-chunk", storage_root=tmp_path)
    assert result["status"] == "unresolved"
    assert result["chunk"] is None
