"""Structured, evidence-linked judgment intelligence records."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class JudgmentAnalysis(Base):
    __tablename__ = "judgment_analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    ingestion_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"), nullable=False)
    source_chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_chunks.id", ondelete="RESTRICT"), nullable=False)
    citation: Mapped[str | None] = mapped_column(String(300))
    case_title: Mapped[str] = mapped_column(String(500), nullable=False)
    court: Mapped[str | None] = mapped_column(String(250))
    decision_date: Mapped[str | None] = mapped_column(String(10))
    bench: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    facts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    issues: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    arguments_petitioner: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    arguments_respondent: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    holdings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ratio_decidendi: Mapped[str | None] = mapped_column(Text)
    final_order: Mapped[str | None] = mapped_column(Text)
    cited_authorities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_review")
    created_by: Mapped[str] = mapped_column(String(100), ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

Index("ix_judgment_analysis_tenant_date", JudgmentAnalysis.tenant_id, JudgmentAnalysis.decision_date)
Index("ix_judgment_analysis_citation", JudgmentAnalysis.citation)
