"""Workspace-scoped, source-linked structured judgment analysis."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.judgment import JudgmentAnalysis
from app.models.ingestion import IngestionJob, IngestionChunk
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user

router = APIRouter(prefix="/research/judgments", tags=["judgment-intelligence"])

class JudgmentAnalysisCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    ingestion_job_id: str = Field(min_length=1, max_length=36)
    source_chunk_id: str = Field(min_length=1, max_length=36)
    case_title: str = Field(min_length=2, max_length=500)
    citation: str | None = Field(default=None, max_length=300)
    court: str | None = Field(default=None, max_length=250)
    decision_date: date | None = None
    bench: list[str] = Field(default_factory=list, max_length=20)
    facts: list[str] = Field(default_factory=list, max_length=100)
    issues: list[str] = Field(default_factory=list, max_length=100)
    arguments_petitioner: list[str] = Field(default_factory=list, max_length=100)
    arguments_respondent: list[str] = Field(default_factory=list, max_length=100)
    holdings: list[str] = Field(default_factory=list, max_length=100)
    ratio_decidendi: str | None = Field(default=None, max_length=20000)
    final_order: str | None = Field(default=None, max_length=10000)
    cited_authorities: list[str] = Field(default_factory=list, max_length=200)
    limitations: list[str] = Field(default_factory=list, max_length=100)

class ReviewUpdate(BaseModel):
    review_status: str
    @field_validator("review_status")
    @classmethod
    def valid_status(cls, v):
        if v not in {"pending_review", "reviewed", "rejected"}:
            raise ValueError("review_status must be pending_review, reviewed, or rejected")
        return v

def _membership(db, tenant_id, user_id):
    return db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id, TenantMembership.user_id == user_id).limit(1))

def _serialize(x):
    return {
        "analysis_id": x.id, "tenant_id": x.tenant_id, "ingestion_job_id": x.ingestion_job_id,
        "source_chunk_id": x.source_chunk_id, "case_title": x.case_title, "citation": x.citation,
        "court": x.court, "decision_date": x.decision_date, "bench": x.bench, "facts": x.facts,
        "issues": x.issues, "arguments_petitioner": x.arguments_petitioner,
        "arguments_respondent": x.arguments_respondent, "holdings": x.holdings,
        "ratio_decidendi": x.ratio_decidendi, "final_order": x.final_order,
        "cited_authorities": x.cited_authorities, "limitations": x.limitations,
        "review_status": x.review_status, "created_at": x.created_at,
        "interpretation_notice": "Structured analysis is a research aid. It is not a substitute for reading the judgment; ratio and holdings require lawyer review."
    }

@router.post("/analyses", status_code=201)
def create_analysis(payload: JudgmentAnalysisCreate, db: Session = Depends(get_db),
                    claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    membership = _membership(db, payload.tenant_id, user_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of the requested workspace.")
    if membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewer role cannot create judgment analyses.")
    job = db.get(IngestionJob, payload.ingestion_job_id)
    chunk = db.get(IngestionChunk, payload.source_chunk_id)
    if not job or not chunk or chunk.job_id != job.id:
        raise HTTPException(status_code=422, detail="source_chunk_id must belong to ingestion_job_id.")
    if job.status not in {"extracted", "needs_ocr"}:
        raise HTTPException(status_code=422, detail="Source judgment must be in an extractable state.")
    data = payload.model_dump()
    data["decision_date"] = payload.decision_date.isoformat() if payload.decision_date else None
    item = JudgmentAnalysis(tenant_id=membership.tenant_id, created_by=user_id, **data)
    db.add(item); db.flush()
    result = _serialize(item); db.commit()
    return result

@router.get("")
def list_analyses(tenant_id: str = Query(min_length=1, max_length=36),
                  citation: str | None = Query(default=None, max_length=300),
                  q: str | None = Query(default=None, max_length=300),
                  limit: int = Query(default=50, ge=1, le=100),
                  db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id or not _membership(db, tenant_id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of the requested workspace.")
    stmt = select(JudgmentAnalysis).where(JudgmentAnalysis.tenant_id == tenant_id)
    if citation:
        stmt = stmt.where(JudgmentAnalysis.citation.ilike(f"%{citation.strip()}%"))
    if q:
        stmt = stmt.where(JudgmentAnalysis.case_title.ilike(f"%{q.strip()}%"))
    items = db.scalars(stmt.order_by(desc(JudgmentAnalysis.created_at)).limit(limit)).all()
    return {"tenant_id": tenant_id, "count": len(items), "analyses": [_serialize(x) for x in items]}

@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db),
                 claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    item = db.get(JudgmentAnalysis, analysis_id)
    if not item or not user_id or not _membership(db, item.tenant_id, user_id):
        raise HTTPException(status_code=404, detail="Judgment analysis not found.")
    return _serialize(item)

@router.patch("/{analysis_id}/review")
def update_review(analysis_id: str, payload: ReviewUpdate, db: Session = Depends(get_db),
                  claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    item = db.get(JudgmentAnalysis, analysis_id)
    if not item or not user_id:
        raise HTTPException(status_code=404, detail="Judgment analysis not found.")
    membership = _membership(db, item.tenant_id, user_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Judgment analysis not found.")
    if membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Only workspace owners or admins can change review status.")
    item.review_status = payload.review_status
    db.commit()
    return _serialize(item)
