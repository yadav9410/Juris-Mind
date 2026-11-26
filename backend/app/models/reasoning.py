"""Workspace-scoped legal issue and argument maps."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def _id(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)

class LegalReasoningWorkspace(Base):
    __tablename__ = "legal_reasoning_workspaces"
    __table_args__ = (Index("ix_legal_reasoning_tenant_created", "tenant_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    fact_summary: Mapped[str] = mapped_column(Text, nullable=False)
    linked_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    linked_assessment_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    issues_json: Mapped[str] = mapped_column(Text, nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
