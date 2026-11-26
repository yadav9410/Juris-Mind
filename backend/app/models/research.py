"""Workspace-scoped research snapshots and immutable evidence references."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchSnapshot(Base):
    """A saved research run: question, plan, status and evidence summary."""

    __tablename__ = "research_snapshots"
    __table_args__ = (
        Index("ix_research_snapshot_tenant_created", "tenant_id", "created_at"),
        Index("ix_research_snapshot_status", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(100))
    court: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class ResearchSnapshotEvidence(Base):
    """A frozen reference to a retrieved passage and its search context."""

    __tablename__ = "research_snapshot_evidence"
    __table_args__ = (
        Index("ix_research_evidence_snapshot", "snapshot_id", "ordinal"),
        Index("ix_research_evidence_tenant", "tenant_id", "snapshot_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("research_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    sub_question: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String(36))
    job_id: Mapped[str | None] = mapped_column(String(36))
    filename: Mapped[str | None] = mapped_column(String(500))
    locator: Mapped[str | None] = mapped_column(String(150))
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
