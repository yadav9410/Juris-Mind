"""Workspace-scoped judicial authority treatment and currentness records.

Treatment assertions are never inferred from citation similarity. Every assertion
must point to a real ingested chunk from the treating judgment. Human review is
recorded as a separate append-only event.
"""
import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.authority import AuthorityTreatment, AuthorityTreatmentReview
from app.models.evidence import EvidenceVerification
from app.models.ingestion import IngestionChunk, IngestionJob
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user

router = APIRouter(prefix="/research/authority", tags=["authority-treatment-currentness"])

TREATMENT_TYPES = {
    "followed", "relied_upon", "applied", "approved", "affirmed",
    "distinguished", "not_followed", "disapproved", "overruled",
    "reversed", "modified", "questioned", "doubted", "referred",
    "stayed", "set_aside", "remanded", "considered",
}
ADVERSE_TYPES = {"overruled", "reversed", "disapproved", "not_followed", "set_aside"}
POSITIVE_TYPES = {"followed", "relied_upon", "applied", "approved", "affirmed"}


class AuthorityTreatmentCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    subject_citation: str = Field(min_length=2, max_length=300)
    subject_title: str | None = Field(default=None, max_length=500)
    subject_job_id: str | None = Field(default=None, max_length=36)
    treatment_type: str
    treatment_scope: str = Field(min_length=10, max_length=5000)
    treating_job_id: str = Field(min_length=1, max_length=36)
    evidence_chunk_id: str = Field(min_length=1, max_length=36)
    evidence_verification_id: str | None = Field(default=None, max_length=36)
    treating_decision_date: date | None = None

    @field_validator("treatment_type")
    @classmethod
    def validate_treatment_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in TREATMENT_TYPES:
            raise ValueError(f"Unsupported treatment_type. Allowed values: {', '.join(sorted(TREATMENT_TYPES))}")
        return normalized


class AuthorityTreatmentReviewCreate(BaseModel):
    decision: str
    note: str = Field(min_length=10, max_length=5000)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"confirmed", "rejected", "needs_further_review"}:
            raise ValueError("decision must be confirmed, rejected, or needs_further_review")
        return normalized


def _member(db: Session, tenant_id: str, user_id: str):
    return db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.user_id == user_id,
    ).limit(1))


def _latest_review(db: Session, treatment_id: str):
    return db.scalar(select(AuthorityTreatmentReview)
        .where(AuthorityTreatmentReview.treatment_id == treatment_id)
        .order_by(desc(AuthorityTreatmentReview.created_at)).limit(1))


def _serialize(db: Session, item: AuthorityTreatment) -> dict:
    review = _latest_review(db, item.id)
    return {
        "treatment_id": item.id,
        "tenant_id": item.tenant_id,
        "subject_authority": {"citation": item.subject_citation, "title": item.subject_title,
                              "ingestion_job_id": item.subject_job_id},
        "treatment": {"type": item.treatment_type, "scope": item.treatment_scope,
                      "decision_date": item.treating_decision_date.isoformat() if item.treating_decision_date else None},
        "treating_authority": {"ingestion_job_id": item.treating_job_id,
                               "evidence_chunk_id": item.evidence_chunk_id},
        "evidence_verification_id": item.evidence_verification_id,
        "source_integrity_status": item.source_integrity_status,
        "review": ({"decision": review.decision, "note": review.note,
                    "reviewer_user_id": review.reviewer_user_id, "reviewed_at": review.created_at}
                   if review else {"decision": "pending", "note": None}),
        "created_at": item.created_at,
        "limitations": [
            "A recorded treatment assertion is not a judicial-status determination.",
            "Evidence-file integrity does not independently prove publisher authenticity or the legal meaning of the passage.",
            "Currentness must be assessed in context, including court hierarchy, bench strength, jurisdiction, proposition and subsequent proceedings.",
        ],
    }


@router.post("/treatments", status_code=201)
def create_treatment(payload: AuthorityTreatmentCreate,
                     db: Session = Depends(get_db),
                     claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    membership = _member(db, payload.tenant_id, user_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of the requested workspace.")
    if membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewer role cannot create authority-treatment records.")

    chunk = db.scalar(select(IngestionChunk).where(IngestionChunk.id == payload.evidence_chunk_id))
    treating_job = db.scalar(select(IngestionJob).where(IngestionJob.id == payload.treating_job_id))
    if not chunk or not treating_job or chunk.job_id != treating_job.id:
        raise HTTPException(status_code=422, detail="Evidence chunk must belong to the supplied treating ingestion job.")
    if treating_job.status not in {"extracted", "needs_ocr"}:
        raise HTTPException(status_code=422, detail="Treating judgment ingestion is not in an extractable state.")

    if payload.subject_job_id:
        subject_job = db.scalar(select(IngestionJob).where(IngestionJob.id == payload.subject_job_id))
        if not subject_job:
            raise HTTPException(status_code=422, detail="subject_job_id does not identify an ingested authority.")

    integrity_status = "not_checked"
    verification_id = None
    if payload.evidence_verification_id:
        verification = db.scalar(select(EvidenceVerification).where(
            EvidenceVerification.id == payload.evidence_verification_id,
            EvidenceVerification.tenant_id == membership.tenant_id,
            EvidenceVerification.chunk_id == chunk.id,
        ))
        if not verification:
            raise HTTPException(status_code=422, detail="Evidence verification must belong to this workspace and the supplied chunk.")
        verification_id = verification.id
        integrity_status = verification.integrity_status

    item = AuthorityTreatment(
        tenant_id=membership.tenant_id, created_by=user_id,
        subject_citation=payload.subject_citation.strip(),
        subject_title=payload.subject_title.strip() if payload.subject_title else None,
        subject_job_id=payload.subject_job_id,
        treatment_type=payload.treatment_type,
        treatment_scope=payload.treatment_scope.strip(),
        treating_job_id=treating_job.id,
        evidence_chunk_id=chunk.id,
        evidence_verification_id=verification_id,
        treating_decision_date=payload.treating_decision_date,
        treatment_review_status="pending",
        source_integrity_status=integrity_status,
    )
    db.add(item)
    db.flush()
    response = _serialize(db, item)
    db.commit()
    return response


@router.post("/treatments/{treatment_id}/review", status_code=201)
def review_treatment(treatment_id: str, payload: AuthorityTreatmentReviewCreate,
                     db: Session = Depends(get_db),
                     claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    item = db.scalar(select(AuthorityTreatment).where(AuthorityTreatment.id == treatment_id))
    if not item:
        raise HTTPException(status_code=404, detail="Authority-treatment record not found.")
    membership = _member(db, item.tenant_id, user_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this workspace.")
    if membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Only workspace owners or admins can record treatment review decisions.")
    review = AuthorityTreatmentReview(
        treatment_id=item.id, tenant_id=item.tenant_id,
        reviewer_user_id=user_id, decision=payload.decision, note=payload.note.strip(),
    )
    db.add(review)
    db.flush()
    response = _serialize(db, item)
    db.commit()
    return response


@router.get("/treatments/{treatment_id}")
def get_treatment(treatment_id: str, db: Session = Depends(get_db),
                  claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    item = db.scalar(select(AuthorityTreatment).join(
        TenantMembership, TenantMembership.tenant_id == AuthorityTreatment.tenant_id
    ).where(AuthorityTreatment.id == treatment_id, TenantMembership.user_id == user_id))
    if not item:
        raise HTTPException(status_code=404, detail="Authority-treatment record not found.")
    return _serialize(db, item)


@router.get("/history")
def authority_history(authority_citation: str = Query(min_length=2, max_length=300),
                      tenant_id: str = Query(min_length=1, max_length=36),
                      db: Session = Depends(get_db),
                      claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    if not _member(db, tenant_id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of the requested workspace.")
    items = db.scalars(select(AuthorityTreatment).where(
        AuthorityTreatment.tenant_id == tenant_id,
        AuthorityTreatment.subject_citation.ilike(authority_citation.strip()),
    ).order_by(desc(AuthorityTreatment.created_at))).all()
    serialized = [_serialize(db, item) for item in items]
    confirmed = [x for x in serialized if x["review"]["decision"] == "confirmed"]
    adverse = [x for x in confirmed if x["treatment"]["type"] in ADVERSE_TYPES]
    positive = [x for x in confirmed if x["treatment"]["type"] in POSITIVE_TYPES]
    return {
        "authority_citation": authority_citation,
        "tenant_id": tenant_id,
        "treatment_count": len(serialized),
        "confirmed_treatment_count": len(confirmed),
        "confirmed_positive_treatment_count": len(positive),
        "confirmed_adverse_treatment_count": len(adverse),
        "currentness_assessment": "review_required",
        "treatments": serialized,
        "notice": "This is a workspace treatment register, not a comprehensive citator. Absence of adverse treatment here does not establish that an authority is good law.",
    }
