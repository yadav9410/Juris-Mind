"""Legal drafting and document-generation workspace.

Stores structured, human-reviewable drafts. It does not make legal determinations
or silently generate authority/citations; source references are supplied explicitly.
"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.drafting import LegalDraft
from app.models.tenant import TenantMembership
from app.security.auth import get_current_user

router = APIRouter(prefix="/drafting", tags=["legal-drafting"])

DOC_TYPES = {"legal_opinion", "memorandum", "pleading", "application", "notice",
             "contract", "due_diligence_report", "research_note", "other"}
STATUSES = {"draft", "in_review", "reviewed", "revision_required", "final"}

class DraftSection(BaseModel):
    heading: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=30000)
    source_refs: list[str] = Field(default_factory=list, max_length=50)

class DraftCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=3, max_length=300)
    document_type: str
    jurisdiction: str = Field(default="India", min_length=2, max_length=120)
    matter_reference: str | None = Field(default=None, max_length=100)
    sections: list[DraftSection] = Field(min_length=1, max_length=40)
    source_refs: list[str] = Field(default_factory=list, max_length=200)

class DraftUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    sections: list[DraftSection] | None = Field(default=None, min_length=1, max_length=40)
    source_refs: list[str] | None = Field(default=None, max_length=200)
    status: str | None = None
    reviewer_notes: str | None = Field(default=None, max_length=10000)

def _member(db, tenant_id, user_id):
    return db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.user_id == user_id).limit(1))

def _get(db, draft_id, user_id):
    return db.scalar(select(LegalDraft).join(
        TenantMembership, TenantMembership.tenant_id == LegalDraft.tenant_id
    ).where(LegalDraft.id == draft_id, TenantMembership.user_id == user_id))

def _payload(row):
    sections = json.loads(row.sections_json)
    refs = json.loads(row.source_refs_json)
    markdown = f"# {row.title}\n\n"
    for section in sections:
        markdown += f"## {section['heading']}\n\n{section['content']}\n\n"
        if section.get("source_refs"):
            markdown += "Source references: " + ", ".join(section["source_refs"]) + "\n\n"
    if refs:
        markdown += "## Source register\n\n" + "\n".join(f"- {ref}" for ref in refs)
    return {
        "draft_id": row.id, "tenant_id": row.tenant_id, "title": row.title,
        "document_type": row.document_type, "jurisdiction": row.jurisdiction,
        "matter_reference": row.matter_reference, "sections": sections,
        "source_refs": refs, "status": row.status, "reviewer_notes": row.reviewer_notes,
        "version": row.version, "created_at": row.created_at, "updated_at": row.updated_at,
        "rendered_markdown": markdown,
        "notice": "Draft content and source references are user-provided. Verify every proposition, quotation, citation and source before professional use."
    }

@router.post("/drafts", status_code=201)
def create_draft(p: DraftCreate, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    uid = claims.get("app_user_id")
    membership = _member(db, p.tenant_id, uid) if uid else None
    if not membership:
        raise HTTPException(403, "Workspace membership is required.")
    if membership.role == "viewer":
        raise HTTPException(403, "Viewer role cannot create drafts.")
    if p.document_type not in DOC_TYPES:
        raise HTTPException(422, f"document_type must be one of: {', '.join(sorted(DOC_TYPES))}")
    row = LegalDraft(tenant_id=p.tenant_id, created_by=uid, title=p.title,
        document_type=p.document_type, jurisdiction=p.jurisdiction,
        matter_reference=p.matter_reference,
        sections_json=json.dumps([s.model_dump() for s in p.sections], ensure_ascii=False),
        source_refs_json=json.dumps(p.source_refs, ensure_ascii=False))
    db.add(row); db.flush(); result = _payload(row); db.commit()
    return result

@router.get("/drafts")
def list_drafts(tenant_id: str = Query(...), limit: int = Query(50, ge=1, le=100),
                db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    uid = claims.get("app_user_id")
    if not uid or not _member(db, tenant_id, uid):
        raise HTTPException(403, "Workspace membership is required.")
    rows = db.scalars(select(LegalDraft).where(LegalDraft.tenant_id == tenant_id)
        .order_by(desc(LegalDraft.updated_at)).limit(limit)).all()
    return {"count": len(rows), "drafts": [_payload(r) for r in rows]}

@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    uid = claims.get("app_user_id")
    row = _get(db, draft_id, uid) if uid else None
    if not row:
        raise HTTPException(404, "Draft not found.")
    return _payload(row)

@router.patch("/drafts/{draft_id}")
def update_draft(draft_id: str, p: DraftUpdate, db: Session = Depends(get_db), claims: dict = Depends(get_current_user)):
    uid = claims.get("app_user_id")
    row = _get(db, draft_id, uid) if uid else None
    if not row:
        raise HTTPException(404, "Draft not found.")
    membership = _member(db, row.tenant_id, uid)
    if membership.role == "viewer":
        raise HTTPException(403, "Viewer role cannot update drafts.")
    data = p.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in STATUSES:
        raise HTTPException(422, f"status must be one of: {', '.join(sorted(STATUSES))}")
    if "title" in data and data["title"] is not None: row.title = data["title"]
    if "sections" in data and data["sections"] is not None:
        row.sections_json = json.dumps([s.model_dump() for s in data["sections"]], ensure_ascii=False)
    if "source_refs" in data and data["source_refs"] is not None:
        row.source_refs_json = json.dumps(data["source_refs"], ensure_ascii=False)
    if "status" in data and data["status"] is not None: row.status = data["status"]
    if "reviewer_notes" in data: row.reviewer_notes = data["reviewer_notes"]
    row.version += 1
    row.updated_at = datetime.now(timezone.utc)
    db.flush(); result = _payload(row); db.commit()
    return result
