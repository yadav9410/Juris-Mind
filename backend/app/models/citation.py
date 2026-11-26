"""Persistent citation candidates and deterministic verification outcomes."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def _id() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.now(timezone.utc)

class CitationReference(Base):
    """A citation extracted from user-provided text within a workspace."""
    __tablename__ = "citation_references"
    __table_args__ = (Index("ix_citation_reference_tenant_created", "tenant_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    source_label: Mapped[str | None] = mapped_column(String(300))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    citation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    normalized_json: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

class VerificationRecord(Base):
    """An immutable, evidence-linked result of a deterministic verification run."""
    __tablename__ = "verification_records"
    __table_args__ = (Index("ix_verification_citation_created", "citation_reference_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    citation_reference_id: Mapped[str] = mapped_column(ForeignKey("citation_references.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False)
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_work_id: Mapped[str | None] = mapped_column(ForeignKey("legal_works.id", ondelete="SET NULL"))
    matched_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id", ondelete="SET NULL"))
    pinpoint_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_applicable")
    authority_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
