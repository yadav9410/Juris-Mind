"""Corpus readiness diagnostics; counts do not certify legal authority."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.ingestion import IngestionChunk, IngestionJob

SEARCHABLE_STATUSES = ("extracted", "needs_ocr")
REVIEWED_STATUSES = ("approved", "corrected")

def get_corpus_readiness(db: Session) -> dict:
    total_jobs = db.scalar(select(func.count()).select_from(IngestionJob)) or 0
    searchable_jobs = db.scalar(select(func.count()).select_from(IngestionJob).where(
        IngestionJob.status.in_(SEARCHABLE_STATUSES))) or 0
    total_chunks = db.scalar(select(func.count()).select_from(IngestionChunk)) or 0
    searchable_chunks = db.scalar(select(func.count()).select_from(IngestionChunk)
        .join(IngestionJob, IngestionJob.id == IngestionChunk.job_id)
        .where(IngestionJob.status.in_(SEARCHABLE_STATUSES))) or 0
    pending = db.scalar(select(func.count()).select_from(IngestionJob).where(
        IngestionJob.status.in_(SEARCHABLE_STATUSES),
        IngestionJob.metadata_review_status == "pending")) or 0
    rejected = db.scalar(select(func.count()).select_from(IngestionJob).where(
        IngestionJob.status.in_(SEARCHABLE_STATUSES),
        IngestionJob.metadata_review_status == "rejected")) or 0
    primary = db.scalar(select(func.count()).select_from(IngestionJob).where(
        IngestionJob.status.in_(SEARCHABLE_STATUSES),
        IngestionJob.source_class == "primary")) or 0
    reviewed = db.scalar(select(func.count()).select_from(IngestionJob).where(
        IngestionJob.status.in_(SEARCHABLE_STATUSES),
        IngestionJob.metadata_review_status.in_(REVIEWED_STATUSES),
        IngestionJob.reviewed_metadata_json.is_not(None))) or 0
    authorities = db.scalar(select(func.count()).select_from(IngestionJob).where(
        IngestionJob.status.in_(SEARCHABLE_STATUSES),
        IngestionJob.metadata_review_status.in_(REVIEWED_STATUSES),
        IngestionJob.authority_verified.is_(True),
        IngestionJob.reviewed_metadata_json.is_not(None),
        IngestionJob.source_class == "primary")) or 0
    return {
        "total_ingestion_jobs": int(total_jobs),
        "searchable_ingestion_jobs": int(searchable_jobs),
        "total_staged_chunks": int(total_chunks),
        "searchable_chunks": int(searchable_chunks),
        "pending_metadata_review": int(pending),
        "reviewed_documents": int(reviewed),
        "rejected_documents": int(rejected),
        "primary_source_documents": int(primary),
        "reviewed_authority_documents": int(authorities),
        "search_ready": searchable_chunks > 0,
        "authority_filtered_search_ready": authorities > 0,
        "next_action": (
            "Run a research query; searchable chunks are available."
            if searchable_chunks else
            "Ingest a PDF or HTML legal source, complete extraction, and stage its chunks."
        ),
        "notice": (
            "Repository counts indicate search availability only. They do not establish "
            "legal authority, currentness, or proposition-to-source support."
        ),
    }
