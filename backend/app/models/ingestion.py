"""Operational records for deterministic document ingestion."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, Integer, String, Text, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def _id():
    return str(uuid.uuid4())

def _now():
    return datetime.now(timezone.utc)

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (Index("ix_ingestion_status_created", "status", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="received")
    storage_key: Mapped[str | None] = mapped_column(Text)
    extracted_text_key: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    classification_json: Mapped[str | None] = mapped_column(Text)
    # Candidate metadata is extracted automatically and remains unverified until review.
    metadata_json: Mapped[str | None] = mapped_column(Text)
    metadata_review_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    reviewed_metadata_json: Mapped[str | None] = mapped_column(Text)
    authority_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    authority_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authority_verified_by: Mapped[str | None] = mapped_column(String(100))
    authority_reference: Mapped[str | None] = mapped_column(Text)
    authority_evidence: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text)
    source_class: Mapped[str] = mapped_column(String(30), default="unverified", nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestionChunk(Base):
    """Search-ready legal passage staged against its source ingestion job."""
    __tablename__ = "ingestion_chunks"
    __table_args__ = (
        Index("ix_ingestion_chunk_job_ordinal", "job_id", "ordinal", unique=True),
        Index("ix_ingestion_chunk_type_locator", "chunk_type", "locator"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(40), nullable=False)
    locator: Mapped[str | None] = mapped_column(String(150))
    heading: Mapped[str | None] = mapped_column(String(500))
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)


class MetadataReviewEvent(Base):
    """Append-only history of human metadata and authority-review decisions."""
    __tablename__ = "metadata_review_events"
    __table_args__ = (Index("ix_metadata_review_job_created", "job_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reviewer_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    previous_metadata_json: Mapped[str | None] = mapped_column(Text)
    resulting_metadata_json: Mapped[str | None] = mapped_column(Text)
    authority_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
