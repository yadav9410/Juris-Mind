"""Persisted, evidence-linked judicial authority treatment records."""
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthorityTreatment(Base):
    """A reported treatment relationship; creation does not imply legal verification."""
    __tablename__ = "authority_treatments"
    __table_args__ = (
        Index("ix_authority_treatment_tenant_created", "tenant_id", "created_at"),
        Index("ix_authority_treatment_subject_citation", "subject_citation"),
        Index("ix_authority_treatment_treating_job", "treating_job_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    subject_citation: Mapped[str] = mapped_column(String(300), nullable=False)
    subject_title: Mapped[str | None] = mapped_column(String(500))
    subject_job_id: Mapped[str | None] = mapped_column(ForeignKey("ingestion_jobs.id", ondelete="SET NULL"))
    treatment_type: Mapped[str] = mapped_column(String(40), nullable=False)
    treatment_scope: Mapped[str] = mapped_column(Text, nullable=False)
    treating_job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"), nullable=False)
    evidence_chunk_id: Mapped[str] = mapped_column(ForeignKey("ingestion_chunks.id", ondelete="RESTRICT"), nullable=False)
    evidence_verification_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_verifications.id", ondelete="SET NULL"))
    treating_decision_date: Mapped[date | None] = mapped_column(Date())
    treatment_review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    source_integrity_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_checked")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class AuthorityTreatmentReview(Base):
    """Append-only human review events for an authority-treatment assertion."""
    __tablename__ = "authority_treatment_reviews"
    __table_args__ = (Index("ix_authority_treatment_review_record", "treatment_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    treatment_id: Mapped[str] = mapped_column(ForeignKey("authority_treatments.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
