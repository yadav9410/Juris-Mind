"""Unified legal reasoning workspace: issues, arguments and links to research/evidence."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.reasoning import LegalReasoningWorkspace
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user

router = APIRouter(prefix="/research/reasoning", tags=["legal-reasoning-workspace"])

class Issue(BaseModel):
    issue: str = Field(min_length=5, max_length=2000)
    legal_test_or_elements: list[str] = Field(default_factory=list, max_length=20)
    facts_supporting: list[str] = Field(default_factory=list, max_length=30)
    facts_against: list[str] = Field(default_factory=list, max_length=30)
    authorities: list[str] = Field(default_factory=list, max_length=30)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    status: str = Field(default="open", pattern="^(open|supported|contested|unresolved)$")

class Argument(BaseModel):
    issue_index: int = Field(ge=0)
    side: str = Field(pattern="^(applicant|respondent|claimant|defendant|other)$")
    proposition: str = Field(min_length=5, max_length=2000)
    supporting_reasons: list[str] = Field(default_factory=list, max_length=20)
    authority_refs: list[str] = Field(default_factory=list, max_length=30)
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)
    counterarguments: list[str] = Field(default_factory=list, max_length=20)

class CreateWorkspace(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=3, max_length=300)
    fact_summary: str = Field(min_length=20, max_length=20000)
    linked_snapshot_id: str | None = Field(default=None, max_length=36)
    linked_assessment_ids: list[str] = Field(default_factory=list, max_length=30)
    issues: list[Issue] = Field(min_length=1, max_length=30)
    arguments: list[Argument] = Field(default_factory=list, max_length=100)

class ReviewUpdate(BaseModel):
    review_status: str = Field(pattern="^(draft|in_review|reviewed|revision_required)$")
    reviewer_notes: str | None = Field(default=None, max_length=10000)

def _member(db, tenant_id, user_id):
    return db.scalar(select(TenantMembership).where(TenantMembership.tenant_id == tenant_id, TenantMembership.user_id == user_id).limit(1))

def _payload(row):
    return {"workspace_id": row.id, "tenant_id": row.tenant_id, "title": row.title,
        "fact_summary": row.fact_summary, "linked_snapshot_id": row.linked_snapshot_id,
        "linked_assessment_ids": json.loads(row.linked_assessment_ids_json),
        "issues": json.loads(row.issues_json), "arguments": json.loads(row.arguments_json),
        "review_status": row.review_status, "reviewer_notes": row.reviewer_notes,
        "created_at": row.created_at, "updated_at": row.updated_at,
        "method_note": "Issues and arguments are user-supplied structured analysis; this endpoint does not independently determine legal correctness."}

@router.post("/workspaces", status_code=201)
def create_workspace(payload: CreateWorkspace, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    membership = _member(db, payload.tenant_id, user_id) if user_id else None
    if not membership: raise HTTPException(403, "Workspace membership is required.")
    if membership.role == "viewer": raise HTTPException(403, "Viewer role cannot create reasoning workspaces.")
    if any(a.issue_index >= len(payload.issues) for a in payload.arguments):
        raise HTTPException(422, "Each argument issue_index must refer to an issue in this workspace.")
    row = LegalReasoningWorkspace(tenant_id=payload.tenant_id, created_by=user_id, title=payload.title,
        fact_summary=payload.fact_summary, linked_snapshot_id=payload.linked_snapshot_id,
        linked_assessment_ids_json=json.dumps(payload.linked_assessment_ids),
        issues_json=json.dumps([x.model_dump() for x in payload.issues], ensure_ascii=False),
        arguments_json=json.dumps([x.model_dump() for x in payload.arguments], ensure_ascii=False))
    db.add(row); db.flush(); result = _payload(row); db.commit(); return result

@router.get("/workspaces")
def list_workspaces(tenant_id: str = Query(...), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id or not _member(db, tenant_id, user_id): raise HTTPException(403, "Workspace membership is required.")
    rows = db.scalars(select(LegalReasoningWorkspace).where(LegalReasoningWorkspace.tenant_id == tenant_id).order_by(LegalReasoningWorkspace.created_at.desc()).limit(limit)).all()
    return {"count": len(rows), "workspaces": [_payload(r) for r in rows]}

@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id: raise HTTPException(403, "Workspace identity is unavailable.")
    row = db.scalar(select(LegalReasoningWorkspace).join(TenantMembership, TenantMembership.tenant_id == LegalReasoningWorkspace.tenant_id).where(LegalReasoningWorkspace.id == workspace_id, TenantMembership.user_id == user_id))
    if not row: raise HTTPException(404, "Reasoning workspace not found.")
    return _payload(row)

@router.patch("/workspaces/{workspace_id}/review")
def update_review(workspace_id: str, payload: ReviewUpdate, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    user_id = claims.get("app_user_id")
    if not user_id: raise HTTPException(403, "Workspace identity is unavailable.")
    row = db.scalar(select(LegalReasoningWorkspace).join(TenantMembership, TenantMembership.tenant_id == LegalReasoningWorkspace.tenant_id).where(LegalReasoningWorkspace.id == workspace_id, TenantMembership.user_id == user_id))
    if not row: raise HTTPException(404, "Reasoning workspace not found.")
    membership = _member(db, row.tenant_id, user_id)
    if membership.role == "viewer": raise HTTPException(403, "Viewer role cannot update review status.")
    row.review_status = payload.review_status; row.reviewer_notes = payload.reviewer_notes
    db.flush(); result = _payload(row); db.commit(); return result
