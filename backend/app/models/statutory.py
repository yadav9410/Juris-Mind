"""Immutable statutory instrument, provision and temporal version records."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StatutoryInstrument(Base):
    __tablename__ = "statutory_instruments"
    __table_args__ = (
        UniqueConstraint("canonical_identifier", name="uq_statutory_instrument_identifier"),
        Index("ix_statutory_instrument_title", "title"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_identifier: Mapped[str] = mapped_column(String(250), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(40), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(150), nullable=False, default="India")
    enactment_date: Mapped[datetime | None] = mapped_column(Date())
    publication_date: Mapped[datetime | None] = mapped_column(Date())
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class StatutoryProvision(Base):
    __tablename__ = "statutory_provisions"
    __table_args__ = (
        UniqueConstraint("instrument_id", "provision_ref", name="uq_statutory_provision_ref"),
        Index("ix_statutory_provision_ref", "provision_ref"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("statutory_instruments.id", ondelete="CASCADE"), nullable=False)
    provision_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    heading: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class StatutoryVersion(Base):
    __tablename__ = "statutory_versions"
    __table_args__ = (
        Index("ix_statutory_version_provision_dates", "provision_id", "effective_from", "effective_to"),
        Index("ix_statutory_version_source_chunk", "source_chunk_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    provision_id: Mapped[str] = mapped_column(ForeignKey("statutory_provisions.id", ondelete="CASCADE"), nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(Date(), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(Date())
    commencement_date: Mapped[datetime | None] = mapped_column(Date())
    publication_date: Mapped[datetime | None] = mapped_column(Date())
    source_job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"), nullable=False)
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("ingestion_chunks.id", ondelete="RESTRICT"), nullable=False)
    evidence_verification_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_verifications.id", ondelete="SET NULL"))
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="unverified")
    closed_by: Mapped[str | None] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class StatutoryEvent(Base):
    __tablename__ = "statutory_events"
    __table_args__ = (
        Index("ix_statutory_event_provision_date", "provision_id", "event_date"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    provision_id: Mapped[str] = mapped_column(ForeignKey("statutory_provisions.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    event_date: Mapped[datetime] = mapped_column(Date(), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amending_instrument: Mapped[str | None] = mapped_column(String(500))
    source_job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id", ondelete="RESTRICT"), nullable=False)
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("ingestion_chunks.id", ondelete="RESTRICT"), nullable=False)
    evidence_verification_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_verifications.id", ondelete="SET NULL"))
    created_by: Mapped[str] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
