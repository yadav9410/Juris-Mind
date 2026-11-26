"""Matter-management, task, audit and report models for the professional workspace."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

def _id(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)

class PlatformMatter(Base):
    __tablename__ = "platform_matters"
    __table_args__ = (Index("ix_platform_matters_tenant_updated", "tenant_id", "updated_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    matter_type: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    reference: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

class PlatformTask(Base):
    __tablename__ = "platform_tasks"
    __table_args__ = (Index("ix_platform_tasks_matter_status", "matter_id", "status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    matter_id: Mapped[str] = mapped_column(ForeignKey("platform_matters.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="todo")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    due_date: Mapped[str | None] = mapped_column(String(10))
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

class PlatformAuditEvent(Base):
    __tablename__ = "platform_audit_events"
    __table_args__ = (Index("ix_platform_audit_tenant_created", "tenant_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"))
    matter_id: Mapped[str | None] = mapped_column(ForeignKey("platform_matters.id", ondelete="SET NULL"))
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

class PlatformReport(Base):
    __tablename__ = "platform_reports"
    __table_args__ = (Index("ix_platform_reports_matter_created", "matter_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    matter_id: Mapped[str] = mapped_column(ForeignKey("platform_matters.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False, default="matter_status")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(30), nullable=False, default="review_required")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
