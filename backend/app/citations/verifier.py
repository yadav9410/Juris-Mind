"""Deterministic matching, pinpoint and authority-status checks."""
from __future__ import annotations
import json
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.legal import LegalWork, LegalDocument, DocumentVersion, LegalProvision, JudgmentParagraph, DocumentEvent

def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

def _authority_status(db: Session, work_id: str | None) -> str:
    if not work_id:
        return "unknown"
    events = db.scalars(select(DocumentEvent).where(DocumentEvent.legal_work_id == work_id).order_by(DocumentEvent.event_date.desc())).all()
    if not events:
        return "unknown"
    latest = events[0].event_type.lower()
    if latest in {"repealed", "overruled"}:
        return "repealed" if latest == "repealed" else "overruled"
    if latest == "amended":
        return "amended"
    if latest in {"enacted", "commenced", "affirmed"}:
        return "recorded_as_in_force" if latest in {"enacted", "commenced"} else "affirmed_event_recorded"
    return "unknown"

def verify_candidate(db: Session, candidate, pinpoint: str | None = None) -> dict:
    """Match case citations/provision references only to records actually in the corpus."""
    normalized = candidate.normalized
    matches = []
    if candidate.citation_type == "statutory":
        ref = normalized.get("provision_ref", "")
        provisions = db.scalars(select(LegalProvision)).all()
        for provision in provisions:
            if _norm(provision.provision_ref) == _norm(ref):
                version = db.get(DocumentVersion, provision.document_version_id)
                document = db.get(LegalDocument, version.document_id) if version else None
                work = db.get(LegalWork, document.legal_work_id) if document else None
                if work:
                    matches.append((work, version, provision))
    else:
        canonical = normalized.get("canonical", candidate.citation_text)
        works = db.scalars(select(LegalWork)).all()
        for work in works:
            identifiers = [work.canonical_identifier, work.title]
            if any(_norm(canonical) == _norm(x) or (_norm(canonical) and _norm(canonical) in _norm(x)) for x in identifiers if x):
                matches.append((work, None, None))
    # Preserve ambiguity; do not guess a unique record.
    unique = {}
    for work, version, provision in matches:
        unique[(work.id, version.id if version else None)] = (work, version, provision)
    matches = list(unique.values())
    if len(matches) == 1:
        work, version, provision = matches[0]
        pinpoint_status = "not_applicable"
        if pinpoint:
            if provision:
                pinpoint_status = "verified" if _norm(pinpoint) == _norm(provision.provision_ref) else "not_found"
            elif version:
                paras = db.scalars(select(JudgmentParagraph).where(JudgmentParagraph.document_version_id == version.id)).all()
                pinpoint_status = "verified" if any(_norm(pinpoint) in {_norm(p.paragraph_number), _norm("paragraph " + p.paragraph_number)} for p in paras) else "not_found"
            else:
                pinpoint_status = "unverifiable"
        return {
            "verification_status": "matched",
            "match_count": 1,
            "matched_work_id": work.id,
            "matched_document_version_id": version.id if version else None,
            "pinpoint_status": pinpoint_status,
            "authority_status": _authority_status(db, work.id),
            "evidence": {"work_title": work.title, "canonical_identifier": work.canonical_identifier,
                         "jurisdiction": work.jurisdiction, "court_name": work.court_name,
                         "version_id": version.id if version else None,
                         "provision_ref": provision.provision_ref if provision else None},
        }
    if len(matches) > 1:
        return {"verification_status": "ambiguous", "match_count": len(matches),
                "matched_work_id": None, "matched_document_version_id": None,
                "pinpoint_status": "unverifiable", "authority_status": "unknown",
                "evidence": {"candidate_work_ids": [m[0].id for m in matches]}}
    return {"verification_status": "not_found", "match_count": 0,
            "matched_work_id": None, "matched_document_version_id": None,
            "pinpoint_status": "unverifiable" if pinpoint else "not_applicable",
            "authority_status": "unknown", "evidence": {"searched_repository": True}}

def persist_verification(db: Session, tenant_id: str, citation_ref, result: dict):
    from app.models.citation import VerificationRecord
    record = VerificationRecord(
        citation_reference_id=citation_ref.id, tenant_id=tenant_id,
        verification_status=result["verification_status"], match_count=result["match_count"],
        matched_work_id=result["matched_work_id"],
        matched_document_version_id=result["matched_document_version_id"],
        pinpoint_status=result["pinpoint_status"], authority_status=result["authority_status"],
        evidence_json=json.dumps(result["evidence"], ensure_ascii=False),
        limitations="Repository match is not proof that the cited passage supports a legal proposition. Authority status is limited to recorded repository events.",
    )
    db.add(record)
    db.flush()
    return record
