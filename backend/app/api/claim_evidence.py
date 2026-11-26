"""Workspace-scoped claim-to-evidence assessment and report retrieval."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.tenant import TenantMembership
from app.models.claim import ResearchClaimAssessment
from app.claims.assessor import assess_claim
from app.security.auth import get_current_user

router = APIRouter(prefix="/research/claims", tags=["claim-evidence-assessment"])

class EvidenceInput(BaseModel):
    evidence_id: str | None = Field(default=None, max_length=100)
    source_label: str | None = Field(default=None, max_length=300)
    locator: str | None = Field(default=None, max_length=100)
    page: int | None = Field(default=None, ge=1)
    text: str = Field(min_length=1, max_length=20000)

class ClaimAssessmentRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    claim: str = Field(min_length=8, max_length=5000)
    evidence: list[EvidenceInput] = Field(min_length=1, max_length=30)

def _member(db: Session, tenant_id: str, user_id: str):
    return db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.user_id == user_id,
    ).limit(1))

@router.post("/assess", status_code=201)
def create_claim_assessment(payload: ClaimAssessmentRequest,
                            db: Session = Depends(get_db),
                            claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    membership = _member(db, payload.tenant_id, user_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of the requested workspace.")
    if membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewer role cannot create claim assessments.")
    result = assess_claim(payload.claim, [item.model_dump() for item in payload.evidence])
    record = ResearchClaimAssessment(
        tenant_id=membership.tenant_id,
        created_by=user_id,
        claim_text=payload.claim,
        assessment_status=result["assessment_status"],
        evidence_json=json.dumps(result["evidence_assessments"], ensure_ascii=False),
        limitations_json=json.dumps(result["limitations"], ensure_ascii=False),
    )
    db.add(record)
    db.flush()
    response = {
        "assessment_id": record.id,
        "tenant_id": record.tenant_id,
        "claim": record.claim_text,
        **result,
        "created_at": record.created_at,
    }
    db.commit()
    return response

@router.get("/{assessment_id}")
def get_claim_assessment(assessment_id: str,
                         db: Session = Depends(get_db),
                         claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    record = db.scalar(
        select(ResearchClaimAssessment)
        .join(TenantMembership, TenantMembership.tenant_id == ResearchClaimAssessment.tenant_id)
        .where(ResearchClaimAssessment.id == assessment_id,
               TenantMembership.user_id == user_id)
    )
    if not record:
        raise HTTPException(status_code=404, detail="Claim assessment not found.")
    return {
        "assessment_id": record.id,
        "tenant_id": record.tenant_id,
        "claim": record.claim_text,
        "assessment_status": record.assessment_status,
        "evidence_assessments": json.loads(record.evidence_json),
        "limitations": json.loads(record.limitations_json),
        "created_at": record.created_at,
    }
