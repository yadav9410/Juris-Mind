"""Tests for the core legal repository database model."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401 - registers every model with Base.metadata
from app.models import LegalWork, SourceRecord, LegalDocument, DocumentVersion


def test_all_expected_tables_are_registered():
    expected = {
        "tenants", "app_users", "tenant_memberships", "legal_works",
        "source_records", "legal_documents", "document_versions",
        "legal_provisions", "judgment_paragraphs", "document_events", "audit_events",
        "research_snapshots", "research_snapshot_evidence",
        "research_agent_runs", "research_agent_outputs",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_legal_work_can_have_multiple_captured_versions():
    # An in-memory database keeps this test isolated and fast.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        work = LegalWork(work_type="act", title="Example Act", canonical_identifier="Act 1 of 2020")
        source = SourceRecord(source_name="Example Gazette", source_class="primary")
        session.add_all([work, source])
        session.flush()

        document = LegalDocument(legal_work_id=work.id, source_id=source.id, document_kind="official_pdf")
        session.add(document)
        session.flush()

        session.add_all([
            DocumentVersion(document_id=document.id, content_sha256="a" * 64),
            DocumentVersion(document_id=document.id, content_sha256="b" * 64),
        ])
        session.commit()

        assert len(document.versions) == 2

    engine.dispose()


def test_document_version_has_hash_uniqueness_constraint():
    # The constraint is declared in model metadata; this guards against accidental removal.
    table = Base.metadata.tables["document_versions"]
    names = {constraint.name for constraint in table.constraints}
    assert "uq_document_version_hash" in names
