"""Tenant-scoped due-diligence matters, risk registers and document comparisons."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def _id(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)

class DueDiligenceMatter(Base):
    __tablename__ = "due_diligence_matters"
    __table_args__ = (Index("ix_dd_matter_tenant_created", "tenant_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    matter_type: Mapped[str] = mapped_column(String(30), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(300), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(120), nullable=False, default="India")
    scope_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

class DueDiligenceRisk(Base):
    __tablename__ = "due_diligence_risks"
    __table_args__ = (Index("ix_dd_risk_matter", "matter_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    matter_id: Mapped[str] = mapped_column(ForeignKey("due_diligence_matters.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    impact: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="identified")
    evidence_refs_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    recommendation: Mapped[str | None] = mapped_column(Text)
    mitigation_owner: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

class DocumentComparison(Base):
    __tablename__ = "due_diligence_document_comparisons"
    __table_args__ = (Index("ix_dd_comparison_matter", "matter_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    matter_id: Mapped[str] = mapped_column(ForeignKey("due_diligence_matters.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    document_label: Mapped[str] = mapped_column(String(300), nullable=False)
    version_a_label: Mapped[str] = mapped_column(String(150), nullable=False)
    version_b_label: Mapped[str] = mapped_column(String(150), nullable=False)
    changes_json: Mapped[str] = mapped_column(Text, nullable=False)
    significance_notes: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
