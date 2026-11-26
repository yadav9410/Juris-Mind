"""Read-only status endpoints for the shared legal-corpus ingestion pipeline.

Document ingestion itself runs through the trusted CLI/worker using the
jurismind_ingest database role. The public API never receives corpus-write access.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ingestion import IngestionChunk, IngestionJob
from app.security.auth import get_current_user

router = APIRouter(prefix="/ingestion", tags=["legal-ingestion"])


@router.get("/jobs/{job_id}")
def get_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
    _claims: dict = Depends(get_current_user),
):
    """Return safe processing metadata without exposing local storage paths."""
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    chunk_count = db.scalar(
        select(func.count()).select_from(IngestionChunk).where(
            IngestionChunk.job_id == job_id
        )
    ) or 0

    classification = json.loads(job.classification_json) if job.classification_json else None
    metadata = json.loads(job.metadata_json) if job.metadata_json else classification

    return {
        "job_id": job.id,
        "filename": job.filename,
        "sha256": job.content_sha256,
        "content_type": job.content_type,
        "status": job.status,
        "page_count": job.page_count,
        "ocr_used": job.ocr_used,
        "classification": classification,
        "metadata_candidates": metadata,
        "metadata_review_status": job.metadata_review_status,
        "reviewed_metadata": json.loads(job.reviewed_metadata_json) if job.reviewed_metadata_json else None,
        "authority_verification": {
            "verified": job.authority_verified,
            "verified_at": job.authority_verified_at,
            "verified_by": job.authority_verified_by,
            "reference": job.authority_reference,
            "evidence": job.authority_evidence,
        },
        "source_provenance": {
            "source_name": job.source_name,
            "source_url": job.source_url,
            "source_class": job.source_class,
        },
        "chunk_count": chunk_count,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "published": False,
        "notice": (
            "This is a staged ingestion record, not a verified or published "
            "legal authority."
        ),
    }
