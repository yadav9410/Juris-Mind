
"""Persistent records for supervised specialist-agent executions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _id() -> str:
    """Generate a UUID string for a database record."""
    return str(uuid.uuid4())


def _now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ResearchAgentRun(Base):
    """One supervisor execution against a saved research snapshot."""

    __tablename__ = "research_agent_runs"

    __table_args__ = (
        Index("ix_agent_runs_tenant_created", "tenant_id", "created_at"),
        Index("ix_agent_runs_snapshot", "snapshot_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_id,
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("research_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )

    initiated_by: Mapped[str] = mapped_column(
        ForeignKey("app_users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    execution_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="mock",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    supervisor_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    limitations: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )


class ResearchAgentOutput(Base):
    """Structured output from one specialist in a supervisor run."""

    __tablename__ = "research_agent_outputs"

    __table_args__ = (
        Index("ix_agent_outputs_run_ordinal", "run_id", "ordinal"),
        Index("ix_agent_outputs_tenant", "tenant_id", "run_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_id,
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_key: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    ordinal: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    output_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
