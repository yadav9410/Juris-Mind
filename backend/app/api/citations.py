"""Authenticated citation extraction and verification endpoints."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.security.auth import get_current_user
from app.models.tenant import TenantMembership
from app.models.citation import CitationReference
from app.citations.extractor import extract_citations
from app.citations.verifier import verify_candidate, persist_verification

router = APIRouter(prefix="/citations", tags=["citation-verification"])

class VerifyTextRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    text: str = Field(min_length=1, max_length=100000)
    source_label: str | None = Field(default=None, max_length=300)
    pinpoints: dict[str, str] = Field(default_factory=dict, description="Optional map from exact extracted citation text to pinpoint text.")

@router.post("/verify")
def verify_text(payload: VerifyTextRequest, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    membership = db.scalar(select(TenantMembership).where(
        TenantMembership.user_id == user_id,
        TenantMembership.tenant_id == payload.tenant_id,
    ).limit(1))
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of the requested workspace.")
    candidates = extract_citations(payload.text)
    results = []
    for candidate in candidates:
        citation = CitationReference(
            tenant_id=membership.tenant_id, created_by=user_id, source_label=payload.source_label,
            raw_text=payload.text, citation_text=candidate.citation_text,
            citation_type=candidate.citation_type, normalized_json=json.dumps(candidate.normalized, ensure_ascii=False),
            start_offset=candidate.start_offset, end_offset=candidate.end_offset,
        )
        db.add(citation)
        db.flush()
        result = verify_candidate(db, candidate, payload.pinpoints.get(candidate.citation_text))
        record = persist_verification(db, membership.tenant_id, citation, result)
        results.append({
            "citation_id": citation.id, "verification_id": record.id,
            "citation_text": candidate.citation_text, "citation_type": candidate.citation_type,
            "normalized": candidate.normalized, **result,
        })
    db.commit()
    return {
        "count": len(results), "results": results,
        "notice": "Automated repository checks only. A match does not establish proposition-to-passage support, current legal effect, or correctness of legal advice. Unknown status means the repository lacks sufficient recorded evidence.",
    }

@router.get("/{citation_id}")
def get_citation(citation_id: str, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    citation = db.scalar(
        select(CitationReference)
        .join(TenantMembership, TenantMembership.tenant_id == CitationReference.tenant_id)
        .where(CitationReference.id == citation_id, TenantMembership.user_id == user_id)
    )
    if not citation:
        raise HTTPException(status_code=404, detail="Citation record not found.")
    from app.models.citation import VerificationRecord
    records = db.scalars(select(VerificationRecord).where(VerificationRecord.citation_reference_id == citation.id).order_by(VerificationRecord.created_at.desc())).all()
    return {"citation_id": citation.id, "citation_text": citation.citation_text,
            "citation_type": citation.citation_type, "normalized": json.loads(citation.normalized_json),
            "verification_history": [{"id": r.id, "status": r.verification_status, "pinpoint_status": r.pinpoint_status,
                                      "authority_status": r.authority_status, "evidence": json.loads(r.evidence_json),
                                      "created_at": r.created_at} for r in records]}
