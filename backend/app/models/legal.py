"""Core legal repository models for JurisMind.

These tables describe legal works, captured source documents, immutable
versions, legal provisions, judgment paragraphs, and source/audit events.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def new_id() -> str:
    """Create a portable UUID string primary key."""
    return str(uuid.uuid4())


class LegalWork(Base):
    """The underlying legal instrument or judgment, independent of its files."""

    __tablename__ = "legal_works"
    __table_args__ = (
        UniqueConstraint("work_type", "canonical_identifier", name="uq_legal_work_identifier"),
        Index("ix_legal_work_type_jurisdiction", "work_type", "jurisdiction"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    work_type: Mapped[str] = mapped_column(String(40), nullable=False)  # act, rule, judgment, notification
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_identifier: Mapped[str | None] = mapped_column(String(250))
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    court_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    documents: Mapped[list["LegalDocument"]] = relationship(back_populates="legal_work")


class SourceRecord(Base):
    """Provenance for a website, publisher, or other source of legal material."""

    __tablename__ = "source_records"
    __table_args__ = (Index("ix_source_classification", "source_class", "source_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_class: Mapped[str] = mapped_column(String(30), nullable=False)  # primary, secondary, unverified
    terms_review_status: Mapped[str] = mapped_column(String(30), default="not_reviewed", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    documents: Mapped[list["LegalDocument"]] = relationship(back_populates="source")


class LegalDocument(Base):
    """A repository record linking a legal work to a captured publication/file."""

    __tablename__ = "legal_documents"
    __table_args__ = (
        Index("ix_legal_document_work", "legal_work_id"),
        Index("ix_legal_document_source", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legal_work_id: Mapped[str] = mapped_column(ForeignKey("legal_works.id", ondelete="RESTRICT"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_records.id", ondelete="RESTRICT"), nullable=False)
    document_kind: Mapped[str] = mapped_column(String(40), nullable=False)  # official_pdf, html_page, scan
    canonical_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    legal_work: Mapped[LegalWork] = relationship(back_populates="documents")
    source: Mapped[SourceRecord] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    """An immutable captured version; later captures create new rows."""

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "content_sha256", name="uq_document_version_hash"),
        Index("ix_document_version_capture", "document_id", "captured_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("legal_documents.id", ondelete="CASCADE"), nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(100))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(Text)  # R2 object key; never a public URL
    extracted_text_key: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified", nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)

    document: Mapped[LegalDocument] = relationship(back_populates="versions")
    provisions: Mapped[list["LegalProvision"]] = relationship(back_populates="document_version", cascade="all, delete-orphan")
    paragraphs: Mapped[list["JudgmentParagraph"]] = relationship(back_populates="document_version", cascade="all, delete-orphan")


class LegalProvision(Base):
    """A structured section, subsection, rule, regulation, or schedule unit."""

    __tablename__ = "legal_provisions"
    __table_args__ = (
        UniqueConstraint("document_version_id", "provision_ref", name="uq_version_provision_ref"),
        Index("ix_provision_ref", "provision_ref"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    provision_ref: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. Section 3(2)
    heading: Mapped[str | None] = mapped_column(String(500))
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)

    document_version: Mapped[DocumentVersion] = relationship(back_populates="provisions")


class JudgmentParagraph(Base):
    """A pinpointable paragraph extracted from a judgment version."""

    __tablename__ = "judgment_paragraphs"
    __table_args__ = (
        UniqueConstraint("document_version_id", "paragraph_number", name="uq_version_paragraph_number"),
        Index("ix_judgment_paragraph_number", "paragraph_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    paragraph_number: Mapped[str] = mapped_column(String(30), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)

    document_version: Mapped[DocumentVersion] = relationship(back_populates="paragraphs")


class DocumentEvent(Base):
    """Records legal events without overwriting earlier legal text or history."""

    __tablename__ = "document_events"
    __table_args__ = (Index("ix_document_event_work_date", "legal_work_id", "event_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    legal_work_id: Mapped[str] = mapped_column(ForeignKey("legal_works.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)  # enacted, commenced, amended, repealed
    event_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    evidence_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id", ondelete="SET NULL"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditEvent(Base):
    """Minimal audit trail for important user and repository actions."""

    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_tenant_created", "tenant_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id", ondelete="SET NULL"))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(30), default="success", nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text)  # JSON text for portability in this first migration
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
