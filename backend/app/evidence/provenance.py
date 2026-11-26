"""Deterministic verification that supplied evidence resolves to ingested source records."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.ingestion import IngestionJob, IngestionChunk

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def _safe_original_path(storage_root: Path, storage_key: str | None) -> Path | None:
    if not storage_key:
        return None
    root = storage_root.resolve()
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate

def verify_chunk_evidence(
    db: Session,
    *,
    chunk_id: str,
    storage_root: str | Path,
    expected_page: int | None = None,
    expected_locator: str | None = None,
    supplied_text: str | None = None,
) -> dict:
    """Resolve a real chunk, compare optional supplied details, and hash its original file."""
    chunk = db.scalar(select(IngestionChunk).where(IngestionChunk.id == chunk_id))
    if chunk is None:
        return {
            "status": "unresolved", "integrity_status": "unavailable",
            "locator_status": "unresolved" if expected_page or expected_locator else "not_supplied",
            "text_status": "unresolved" if supplied_text else "not_supplied",
            "reasons": ["No ingested passage matches the supplied chunk_id."],
            "job": None, "chunk": None, "stored_document_sha256": None,
            "observed_document_sha256": None, "chunk_text_sha256": None,
        }
    job = db.scalar(select(IngestionJob).where(IngestionJob.id == chunk.job_id))
    if job is None:
        return {
            "status": "unresolved", "integrity_status": "unavailable",
            "locator_status": "unresolved", "text_status": "unresolved",
            "reasons": ["The passage exists but its ingestion job is missing."],
            "job": None, "chunk": chunk, "stored_document_sha256": None,
            "observed_document_sha256": None, "chunk_text_sha256": hashlib.sha256(chunk.body_text.encode("utf-8")).hexdigest(),
        }

    reasons = []
    path = _safe_original_path(Path(storage_root), job.storage_key)
    observed_hash = None
    if path is None or not path.is_file():
        integrity_status = "unavailable"
        reasons.append("The original file is not available in the configured storage location.")
    else:
        observed_hash = sha256_file(path)
        integrity_status = "matched" if observed_hash == job.content_sha256 else "mismatch"
        if integrity_status == "mismatch":
            reasons.append("The original file SHA-256 does not match the ingestion record.")

    locator_checks = []
    if expected_page is not None:
        page_match = chunk.page_start is not None and chunk.page_start <= expected_page <= (chunk.page_end or chunk.page_start)
        locator_checks.append(page_match)
        if not page_match:
            reasons.append("The supplied page does not match the stored passage page range.")
    if expected_locator is not None:
        locator_match = (chunk.locator or "").strip().casefold() == expected_locator.strip().casefold()
        locator_checks.append(locator_match)
        if not locator_match:
            reasons.append("The supplied locator does not match the stored passage locator.")
    locator_status = "not_supplied" if not locator_checks else ("matched" if all(locator_checks) else "mismatch")

    if supplied_text is None:
        text_status = "not_supplied"
    else:
        normalized_supplied = " ".join(supplied_text.split())
        normalized_stored = " ".join(chunk.body_text.split())
        text_status = "matched" if normalized_supplied == normalized_stored else "mismatch"
        if text_status == "mismatch":
            reasons.append("The supplied passage text differs from the canonical stored chunk text.")

    chunk_text_hash = hashlib.sha256(chunk.body_text.encode("utf-8")).hexdigest()
    if integrity_status == "mismatch" or locator_status == "mismatch" or text_status == "mismatch":
        status = "unresolved"
    elif integrity_status == "matched":
        status = "verified"
        reasons.append("The evidence resolves to a stored ingestion chunk and the original file hash matches the ingestion record.")
    else:
        status = "partially_verified"
        reasons.append("The passage record is linked, but original-file integrity could not be confirmed.")

    return {
        "status": status, "integrity_status": integrity_status,
        "locator_status": locator_status, "text_status": text_status,
        "reasons": reasons, "job": job, "chunk": chunk,
        "stored_document_sha256": job.content_sha256,
        "observed_document_sha256": observed_hash,
        "chunk_text_sha256": chunk_text_hash,
    }
