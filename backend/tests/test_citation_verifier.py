import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
import app.models  # noqa
from app.models.tenant import Tenant, AppUser
from app.models.legal import LegalWork, SourceRecord, LegalDocument, DocumentVersion, LegalProvision, DocumentEvent
from app.citations.extractor import extract_citations
from app.citations.verifier import verify_candidate

def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

def test_statutory_citation_matches_provision_and_checks_pinpoint():
    engine = setup_db()
    with Session(engine) as db:
        tenant = Tenant(id="t1", name="Workspace")
        user = AppUser(id="u1", email="test@example.com")
        source = SourceRecord(id="s1", source_name="Official", source_class="primary")
        work = LegalWork(id="w1", work_type="act", title="Example Act", canonical_identifier="Example Act", jurisdiction="India")
        doc = LegalDocument(id="d1", legal_work_id="w1", source_id="s1", document_kind="official_pdf")
        version = DocumentVersion(id="v1", document_id="d1", content_sha256="a"*64)
        provision = LegalProvision(id="p1", document_version_id="v1", provision_ref="Section 3(2)", body_text="Provision text")
        db.add_all([tenant,user,source,work,doc,version,provision])
        db.commit()
        candidate = extract_citations("Section 3(2)")[0]
        result = verify_candidate(db, candidate, "Section 3(2)")
        assert result["verification_status"] == "matched"
        assert result["pinpoint_status"] == "verified"
        assert result["matched_work_id"] == "w1"

def test_missing_citation_returns_not_found_and_unknown_status():
    engine = setup_db()
    with Session(engine) as db:
        candidate = extract_citations("2024 INSC 123")[0]
        result = verify_candidate(db, candidate)
        assert result["verification_status"] == "not_found"
        assert result["authority_status"] == "unknown"

def test_authority_status_uses_latest_recorded_event_only():
    engine = setup_db()
    with Session(engine) as db:
        source = SourceRecord(id="s1", source_name="Official", source_class="primary")
        work = LegalWork(id="w1", work_type="act", title="Example Act", canonical_identifier="Example Act")
        db.add_all([source, work])
        db.flush()
        from datetime import datetime, timezone
        db.add(DocumentEvent(legal_work_id="w1", event_type="enacted", event_date=datetime(2000,1,1,tzinfo=timezone.utc)))
        db.add(DocumentEvent(legal_work_id="w1", event_type="amended", event_date=datetime(2020,1,1,tzinfo=timezone.utc)))
        db.commit()
        candidate = extract_citations("Example Act")[0] if extract_citations("Example Act") else None
        # Directly verify the authority-status helper because free-form act titles
        # are not treated as citations by the extractor.
        from app.citations.verifier import _authority_status
        assert _authority_status(db, "w1") == "amended"
