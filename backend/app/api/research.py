"""Authenticated workspace-scoped research APIs."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.research import ResearchSnapshot, ResearchSnapshotEvidence
from app.models.research_job import ResearchJob
from app.research.job_service import enqueue_research_job
from app.research.diagnostics import get_corpus_readiness
from app.models.tenant import TenantMembership
from app.research.orchestrator import run_research
from app.security.auth import get_current_user

router = APIRouter(prefix="/research", tags=["legal-research-orchestration"])

class ResearchRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    question: str = Field(min_length=8, max_length=5000)
    jurisdiction: str | None = Field(default=None, max_length=100)
    court: str | None = Field(default=None, max_length=200)
    document_type: str | None = Field(default=None, max_length=40)
    authoritative_only: bool = False
    sub_questions: list[str] | None = Field(default=None, max_length=8)
    per_query_limit: int = Field(default=10, ge=1, le=25)


class ExternalDiscoveryRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    question: str = Field(min_length=3, max_length=500)
    jurisdiction: str | None = Field(default=None, max_length=100)
    court: str | None = Field(default=None, max_length=200)
    categories: list[str] | None = Field(default=None, max_length=3)

@router.get("/sources")
def get_official_research_sources(db: Session = Depends(get_db),
                                 claims: dict = Depends(get_current_user),
                                 tenant_id: str = Query(..., min_length=1, max_length=36)):
    user_id = claims.get("app_user_id")
    membership = _membership(db, tenant_id, user_id) if user_id else None
    if not membership:
        raise HTTPException(status_code=403, detail="Workspace permission is required.")
    from app.sources.discovery import list_official_sources
    return {"source_priority": "official_government_and_courts_first",
            "sources": list_official_sources()}

@router.post("/search/official")
def search_official_sources_api(payload: ExternalDiscoveryRequest, db: Session = Depends(get_db),
                                claims: dict = Depends(get_current_user)):
    """Search official legal domains and retrieve permitted original documents."""
    user_id = claims.get("app_user_id")
    membership = _membership(db, payload.tenant_id, user_id) if user_id else None
    if not membership or membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Workspace permission is required.")
    from app.sources.external_research import (
        search_official_sources, ExternalSearchNotConfigured,
    )
    try:
        return search_official_sources(
            payload.question, jurisdiction=payload.jurisdiction, court=payload.court,
            categories=payload.categories,
        )
    except ExternalSearchNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/discover/official")
def discover_official_sources(payload: ExternalDiscoveryRequest, db: Session = Depends(get_db),
                              claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    membership = _membership(db, payload.tenant_id, user_id) if user_id else None
    if not membership or membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Workspace permission is required.")
    from app.sources.discovery import build_official_discovery_plan
    try:
        return build_official_discovery_plan(payload.question, jurisdiction=payload.jurisdiction,
                                             court=payload.court, categories=payload.categories)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _membership(db: Session, tenant_id: str, user_id: str):
    return db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.user_id == user_id,
    ).limit(1))


class ResearchJobRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    question: str = Field(min_length=8, max_length=5000)
    jurisdiction: str | None = Field(default=None, max_length=100)
    court: str | None = Field(default=None, max_length=200)

@router.post("/jobs", status_code=202)
def create_research_job(payload: ResearchJobRequest, db: Session = Depends(get_db),
                        claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    membership = _membership(db, payload.tenant_id, user_id)
    if not membership or membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Workspace permission is required.")
    job = enqueue_research_job(db, tenant_id=payload.tenant_id, user_id=user_id,
                               question=payload.question, jurisdiction=payload.jurisdiction,
                               court=payload.court)
    db.commit()
    return {"job_id": job.id, "status": job.status, "stage": job.stage, "progress": job.progress}

@router.get("/jobs/{job_id}")
def get_research_job(job_id: str, db: Session = Depends(get_db),
                     claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    job = db.scalar(select(ResearchJob).join(TenantMembership,
        TenantMembership.tenant_id == ResearchJob.tenant_id).where(
        ResearchJob.id == job_id, TenantMembership.user_id == user_id))
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found.")
    try:
        result = json.loads(job.result_json or "{}")
    except json.JSONDecodeError:
        result = {}
    return {"job_id": job.id, "status": job.status, "stage": job.stage,
            "progress": job.progress, "legislation_status": job.legislation_status,
            "case_law_status": job.case_law_status, "result": result,
            "error": job.error_message, "created_at": job.created_at,
            "completed_at": job.completed_at}

def _json_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}

def _snapshot_payload(snapshot: ResearchSnapshot) -> dict:
    return {
        "snapshot_id": snapshot.id, "tenant_id": snapshot.tenant_id,
        "question": snapshot.question, "jurisdiction": snapshot.jurisdiction,
        "court": snapshot.court, "status": snapshot.status,
        "plan": _json_object(snapshot.plan_json),
        "summary": _json_object(snapshot.summary_json),
        "limitations": snapshot.limitations, "created_at": snapshot.created_at,
    }

@router.get("/corpus-readiness")
def corpus_readiness(db: Session = Depends(get_db), _claims: dict = Depends(get_current_user)):
    return get_corpus_readiness(db)

@router.post("/snapshots", status_code=201)
def create_research_snapshot(
    payload: ResearchRequest, db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    membership = _membership(db, payload.tenant_id, user_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of the requested workspace.")
    if membership.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewer role cannot create research snapshots.")
    try:
        snapshot = run_research(
            db, tenant_id=payload.tenant_id, user_id=user_id,
            question=payload.question, jurisdiction=payload.jurisdiction,
            court=payload.court, document_type=payload.document_type,
            authoritative_only=payload.authoritative_only,
            supplied_sub_questions=payload.sub_questions,
            per_query_limit=payload.per_query_limit,
        )
        db.flush()
        db.refresh(snapshot)
        response_payload = _snapshot_payload(snapshot)
        db.commit()
        return response_payload
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        print("\\n========== RESEARCH DATABASE FAILURE ==========")
        print("ERROR TYPE:", type(exc).__name__)
        print("ERROR:", repr(exc))
        print("ORIGINAL ERROR:", repr(getattr(exc, "orig", None)))
        print("FAILED SQL:", getattr(exc, "statement", None))
        print("SQL PARAMETERS:", getattr(exc, "params", None))
        print("================================================\\n")
        raise HTTPException(status_code=503, detail="Research database operation failed. Check the API terminal.") from exc
    except Exception:
        db.rollback()
        raise

@router.get("/snapshots")
def list_research_snapshots(
    tenant_id: str = Query(..., min_length=1, max_length=36),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), claims: dict = Depends(get_current_user),
):
    user_id = claims.get("app_user_id")
    if not user_id or not _membership(db, tenant_id, user_id):
        raise HTTPException(status_code=403, detail="Workspace membership is required.")
    rows = db.scalars(select(ResearchSnapshot)
        .where(ResearchSnapshot.tenant_id == tenant_id)
        .order_by(ResearchSnapshot.created_at.desc()).limit(limit)).all()
    return {"count": len(rows), "snapshots": [_snapshot_payload(row) for row in rows]}

@router.get("/snapshots/{snapshot_id}")
def get_research_snapshot(
    snapshot_id: str, db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user),
):
    user_id = claims.get("app_user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="Workspace identity is unavailable.")
    snapshot = db.scalar(select(ResearchSnapshot)
        .join(TenantMembership, TenantMembership.tenant_id == ResearchSnapshot.tenant_id)
        .where(ResearchSnapshot.id == snapshot_id, TenantMembership.user_id == user_id))
    if not snapshot:
        raise HTTPException(status_code=404, detail="Research snapshot not found.")
    evidence_rows = db.scalars(select(ResearchSnapshotEvidence).where(
        ResearchSnapshotEvidence.snapshot_id == snapshot.id,
        ResearchSnapshotEvidence.tenant_id == snapshot.tenant_id,
    ).order_by(ResearchSnapshotEvidence.ordinal.asc())).all()
    payload = _snapshot_payload(snapshot)
    payload["evidence"] = [{
        "ordinal": row.ordinal, "sub_question": row.sub_question,
        "chunk_id": row.chunk_id, "job_id": row.job_id,
        "filename": row.filename, "locator": row.locator,
        "page_start": row.page_start, "page_end": row.page_end,
        "captured_at": row.captured_at,
        "retrieved_fields": _json_object(row.evidence_json),
    } for row in evidence_rows]
    return payload
