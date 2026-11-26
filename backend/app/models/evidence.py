"""Persisted source-provenance and evidence-integrity verification records."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def _id() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.now(timezone.utc)

class EvidenceVerification(Base):
    __tablename__ = "evidence_verifications"
    __table_args__ = (
        Index("ix_evidence_verification_tenant_created", "tenant_id", "created_at"),
        Index("ix_evidence_verification_chunk", "chunk_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    integrity_status: Mapped[str] = mapped_column(String(30), nullable=False)
    locator_status: Mapped[str] = mapped_column(String(30), nullable=False)
    text_status: Mapped[str] = mapped_column(String(30), nullable=False)
    stored_document_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_document_sha256: Mapped[str | None] = mapped_column(String(64))
    chunk_text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text)
    source_class: Mapped[str] = mapped_column(String(30), nullable=False)
    page_start: Mapped[int | None] = mapped_column()
    page_end: Mapped[int | None] = mapped_column()
    locator: Mapped[str | None] = mapped_column(String(150))
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False)
    authenticity_status: Mapped[str] = mapped_column(String(50), nullable=False, default="not_independently_authenticated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
