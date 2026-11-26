"""Regenerate candidate metadata for pending jobs without changing chunks."""
from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.ingestion import IngestionJob
from app.ingestion.classifier import classify_legal_text

def reprocess_metadata(job_id: str) -> dict:
    settings = get_settings()
    if not settings.ingestion_database_url:
        raise RuntimeError("INGESTION_DATABASE_URL is not configured.")
    storage_root = Path(settings.ingestion_storage_dir).resolve()
    engine = create_engine(settings.ingestion_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as db:
            job = db.get(IngestionJob, job_id)
            if job is None:
                raise ValueError(f"Ingestion job not found: {job_id}")
            if job.status not in {"extracted", "needs_ocr"}:
                raise ValueError(f"Cannot reprocess metadata for status: {job.status}")
            if job.metadata_review_status != "pending":
                raise ValueError("Only pending metadata can be reprocessed. Reviewed records must use the human-review workflow.")
            if not job.extracted_text_key:
                raise ValueError("Job has no saved extracted-text path.")
            text_path = (storage_root / job.extracted_text_key).resolve()
            if not text_path.is_relative_to(storage_root):
                raise ValueError("Invalid extracted-text storage path.")
            if not text_path.is_file():
                raise FileNotFoundError(f"Extracted text file not found: {text_path}")
            extracted_text = text_path.read_text(encoding="utf-8")
            candidates = classify_legal_text(extracted_text, job.filename)
            metadata = {**candidates, "metadata_origin": "automated_candidate_extraction", "verified": False}
            job.classification_json = json.dumps(candidates, ensure_ascii=False)
            job.metadata_json = json.dumps(metadata, ensure_ascii=False)
            # Reviewed metadata, authority decisions, provenance and chunks remain untouched.
            db.commit()
            return {
                "job_id": str(job.id),
                "filename": job.filename,
                "metadata_review_status": job.metadata_review_status,
                "metadata": metadata,
                "preserved": ["original job ID", "SHA-256 hash", "original file", "ingestion status", "source provenance fields", "reviewed metadata and authority fields", "existing chunks"],
            }
    finally:
        engine.dispose()
